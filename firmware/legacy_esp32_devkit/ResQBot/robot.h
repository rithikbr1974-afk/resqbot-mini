// The robot's brain: manual driving, autonomous search, survivor confirmation and the event log.
#pragma once
#include <Arduino.h>
#include "config.h"
#include "motors.h"
#include "sensors.h"
#include "thermal.h"
#include "detection.h"

enum Mode { MODE_MANUAL, MODE_AUTO, MODE_ESTOP };
enum AutoState { A_IDLE, A_SCAN, A_ALIGN, A_APPROACH, A_CONFIRM, A_ALERT, A_CRUISE, A_AVOID };

static const char *MODE_NAMES[] = {"manual", "auto", "estop"};
static const char *STATE_NAMES[] = {"idle", "scanning", "turning to target", "approaching",
                                    "confirming", "SURVIVOR ALERT", "searching", "avoiding obstacle"};

struct Event {
  uint32_t ms;
  char kind[10];      // survivor | possible | heat | hazard | info
  char text[72];
  int score;
};

class Robot {
 public:
  Motors motors;
  Sensors sensors;
  ThermalScanner scanner;

  Mode mode = MODE_MANUAL;
  AutoState state = A_IDLE;
  Finding finding;          // result of the last sweep
  int score = 0;            // confidence of the current/last target
  bool motionSeen = false;
  float closeReading = NAN;
  bool thermalOk = false;
  uint32_t survivors = 0;

  static const int LOG_SIZE = 24;
  Event log[LOG_SIZE];
  int logCount = 0;         // total ever written (newest is (logCount-1) % LOG_SIZE)

  void begin() {
    motors.begin();
    sensors.begin();
    thermalOk = scanner.begin();
    addEvent("info", thermalOk ? "Robot ready, thermal sensor OK" : "Thermal sensor NOT found - check wiring", 0);
  }

  // ---------------- commands from the dashboard ----------------
  void setMode(Mode m) {
    motors.stop();
    sensors.alertPattern(false);
    mode = m;
    state = A_IDLE;
    if (m == MODE_AUTO) {
      if (sensors.batteryLow()) { mode = MODE_MANUAL; addEvent("hazard", "Battery low - search not started", 0); return; }
      startScan();
      addEvent("info", "Autonomous search started", 0);
    } else if (m == MODE_ESTOP) {
      addEvent("info", "EMERGENCY STOP", 0);
    }
  }

  void manualDrive(int left, int right) {
    if (mode != MODE_MANUAL) return;
    if (left > 0 && right > 0 && sensors.distanceCm < OBSTACLE_CM / 2) left = right = 0;  // don't ram anything
    motors.drive(left, right);
    lastCmd_ = millis();
  }

  void requestScan() {                     // one sweep while standing still (manual mode)
    if (mode == MODE_MANUAL && !scanner.busy()) { motors.stop(); startScan(); }
  }

  void acknowledge() {                     // rescuers have the location: resume searching
    if (state != A_ALERT) return;
    sensors.alertPattern(false);
    addEvent("info", "Alert acknowledged, search resumed", score);
    turnAway();
  }

  // ---------------- main loop ----------------
  void update() {
    sensors.update();
    uint32_t now = millis();
    if (!scanner.busy() && now - lastLive_ > 400) {   // live reading straight ahead for the dashboard
      lastLive_ = now;
      scanner.readAhead();
      scanner.ambient = scanner.mlx.ambient();
    }

    if (sensors.gasAlarm() != gasWas_) {
      gasWas_ = sensors.gasAlarm();
      if (gasWas_) addEvent("hazard", "Smoke / gas detected - rescuers use breathing protection", 0);
    }

    if (mode == MODE_ESTOP) { motors.stop(); return; }

    if (mode == MODE_MANUAL) {
      if (motors.moving() && now - lastCmd_ > MANUAL_TIMEOUT_MS) motors.stop();   // dead-man
      if (scanner.busy() && scanner.step()) afterScan(false);
      return;
    }

    // ---- MODE_AUTO ----
    if (sensors.batteryLow()) { setMode(MODE_MANUAL); addEvent("hazard", "Battery low - search stopped", 0); return; }

    switch (state) {
      case A_SCAN:
        if (scanner.step()) afterScan(true);
        break;

      case A_ALIGN:
        if (now >= until_) {
          motors.stop();
          scanner.aim(PAN_CENTER, TILT_ANGLES[finding.row]);
          closeReading = NAN;
          enter(A_APPROACH, 4000);         // crawl at most 4 s toward the heat
        }
        break;

      case A_APPROACH: {
        if (now - lastRead_ > 200) {
          lastRead_ = now;
          float t = scanner.readAhead();
          if (!isnan(t) && (isnan(closeReading) || t > closeReading)) closeReading = t;
        }
        bool close = sensors.distanceCm <= APPROACH_STOP_CM;
        if (close || now >= until_) {
          motors.stop();
          motionSeen = false;
          enter(A_CONFIRM, CONFIRM_MS + 1000);   // first second lets the PIR settle after moving
        } else {
          motors.forward(CRAWL_SPEED);
        }
        break;
      }

      case A_CONFIRM:
        if (now - enteredAt_ > 1000 && sensors.motion) motionSeen = true;
        if (now - lastRead_ > 300) {
          lastRead_ = now;
          float t = scanner.readAhead();
          if (!isnan(t) && (isnan(closeReading) || t > closeReading)) closeReading = t;
        }
        if (now >= until_) decide();
        break;

      case A_ALERT:
        sensors.alertPattern(true);        // stays here as a beacon until acknowledged
        break;

      case A_CRUISE:
        if (sensors.distanceCm < OBSTACLE_CM) { avoid(); break; }
        motors.forward(DRIVE_SPEED);
        if (now >= until_) { motors.stop(); startScan(); }
        break;

      case A_AVOID:
        if (now >= until_) {
          if (avoidPhase_ == 0) {          // backed up, now turn
            avoidPhase_ = 1;
            random(2) ? motors.turnLeft(TURN_SPEED) : motors.turnRight(TURN_SPEED);
            until_ = now + 500 + random(500);
          } else {
            motors.stop();
            enter(A_CRUISE, CRUISE_MS);
          }
        }
        break;

      default:
        break;
    }
  }

  void addEvent(const char *kind, const char *text, int s) {
    Event &e = log[logCount % LOG_SIZE];
    e.ms = millis();
    strncpy(e.kind, kind, sizeof(e.kind) - 1); e.kind[sizeof(e.kind) - 1] = 0;
    strncpy(e.text, text, sizeof(e.text) - 1); e.text[sizeof(e.text) - 1] = 0;
    e.score = s;
    logCount++;
    Serial.printf("[%7.1fs] %-8s %s (%d)\n", e.ms / 1000.0, kind, text, s);
  }

  const char *stateName() const {
    if (mode == MODE_MANUAL) return scanner.busy() ? "scanning" : "manual control";
    if (mode == MODE_ESTOP) return "STOPPED";
    return STATE_NAMES[state];
  }

 private:
  uint32_t until_ = 0, enteredAt_ = 0, lastCmd_ = 0, lastRead_ = 0, lastLive_ = 0;
  int avoidPhase_ = 0;
  bool gasWas_ = false;

  void enter(AutoState s, uint32_t forMs) { state = s; enteredAt_ = millis(); until_ = enteredAt_ + forMs; }

  void startScan() {
    motors.stop();
    scanner.start();
    state = A_SCAN;
  }

  void afterScan(bool autoMode) {
    finding = analyzeSweep(&scanner.grid[0][0], TILT_ROWS, SCAN_COLS);
    char msg[72];
    if (finding.fire) {
      snprintf(msg, sizeof msg, "Hot spot %.0f C - possible fire", finding.hottest);
      addEvent("hazard", msg, 0);
    }
    if (finding.found) {
      score = confidenceScore(finding, NAN, false);
      int bearing = (int)lroundf(finding.panAngle - PAN_CENTER);   // + = left of the robot
      snprintf(msg, sizeof msg, "Heat signature %.1f C (+%.1f) at %d deg %s",
               finding.peak, finding.delta, abs(bearing), bearing >= 0 ? "left" : "right");
      addEvent("heat", msg, score);
    } else {
      score = 0;
    }
    if (!autoMode) { state = A_IDLE; return; }

    if (finding.found) {                   // turn the whole robot toward the heat
      float turn = finding.panAngle - PAN_CENTER;
      uint32_t ms = (uint32_t)(fabsf(turn) / TURN_DEG_PER_SEC * 1000);
      if (turn > 0) motors.turnLeft(TURN_SPEED); else motors.turnRight(TURN_SPEED);
      enter(A_ALIGN, ms);
    } else {
      enter(A_CRUISE, CRUISE_MS);
    }
  }

  void decide() {
    score = confidenceScore(finding, closeReading, motionSeen);
    char msg[72];
    if (score >= ALERT_SCORE) {
      survivors++;
      snprintf(msg, sizeof msg, "SURVIVOR LIKELY - %s, %.1f C at %.0f cm",
               motionSeen ? "moving" : "NOT moving (may be unconscious)", closeReading, sensors.distanceCm);
      addEvent("survivor", msg, score);
      state = A_ALERT;
    } else if (score >= POSSIBLE_SCORE) {
      snprintf(msg, sizeof msg, "Possible survivor, check manually (%.1f C)", closeReading);
      addEvent("possible", msg, score);
      turnAway();
    } else {
      addEvent("info", "Heat source rejected (not body-like)", score);
      turnAway();
    }
  }

  // Back up and spin so the same heat source is not found again straight away.
  void turnAway() {
    motors.backward(DRIVE_SPEED);
    avoidPhase_ = 0;
    enter(A_AVOID, 500);
  }

  void avoid() {
    motors.backward(DRIVE_SPEED);
    avoidPhase_ = 0;
    enter(A_AVOID, 400);
  }
};
