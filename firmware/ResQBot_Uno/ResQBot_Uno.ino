/*
  ResQBot Mini - Arduino Uno main board
  -------------------------------------
  Reads every sensor (MLX90614 thermal on a pan-tilt, DHT11, HC-SR04, HC-SR501 PIR, MQ-2, battery),
  runs the survivor search, drives the L298N motors, servos, buzzer and beacon, and talks to the
  ESP32-CAM over the hardware Serial port (D0/D1):

    Uno -> CAM   "S{...json status...}"  every 400 ms
                 "E,<kind>,<score>,<text>"  one line per event
    CAM -> Uno   "D,<left>,<right>"  drive (-255..255, manual mode, repeated every 200 ms)
                 "M,manual" | "M,auto" | "M,estop"   "C" scan   "A" acknowledge   "B" beep
                 "L,1" | "L,0"  car LED (headlight) on / off
                 "R,1" | "R,0"  drill on / off (manual mode only, repeated while the button is held)
                 Every command ends with "*XX", the XOR of its characters in hex. A line damaged on the wire
                 (bytes are lost while the DHT11 is read) fails the check and is ignored; drive is resent anyway.

  The ESP32-CAM (firmware/ResQCam_Gateway) shows all of this on the phone dashboard with live video.
  Libraries: Servo, Wire (built in), "DHT sensor library" + "Adafruit Unified Sensor" (Library Manager).
  Unplug the wire on D0 (or switch the robot off) while uploading to the Uno.
*/
#include <Wire.h>
#include <Servo.h>
#include <DHT.h>
#include "config.h"
#include "detection.h"

#if BATTERY_MONITOR
static_assert(PIN_DRILL != PIN_BATTERY, "The drill and the battery divider can't share A1: set BATTERY_MONITOR false");
#endif
const int SCAN_COLS = (PAN_MAX - PAN_MIN) / PAN_STEP + 1;

enum Mode : uint8_t { MODE_MANUAL, MODE_AUTO, MODE_ESTOP };
enum AutoState : uint8_t { A_IDLE, A_SCAN, A_ALIGN, A_APPROACH, A_CONFIRM, A_ALERT, A_CRUISE, A_AVOID };
const char *const MODE_NAMES[] = {"manual", "auto", "estop"};
const char *const STATE_NAMES[] = {"idle", "scanning", "turning to target", "approaching", "confirming",
                                   "SURVIVOR ALERT", "searching", "avoiding obstacle"};

Servo panServo, tiltServo;
DHT dht(PIN_DHT, DHT11);

// ---- sensor values ----
float grid[TILT_ROWS][SCAN_COLS], work[TILT_ROWS][SCAN_COLS];
float lastObject = NAN, ambient = NAN, airTemp = NAN, humidity = NAN;
float distanceCm = 400, batteryV = 0;
int gasRaw = 0;
bool motion = false, thermalOk = false, dhtOk = false;

// ---- robot state ----
Mode mode = MODE_MANUAL;
AutoState state = A_IDLE;
Finding finding;
int score = 0;
bool motionSeen = false, moving = false, gasWas = false, patternOn = false, blocked = false;
float closeReading = NAN;
uint16_t survivors = 0, scanCount = 0;

// ---- scanner ----
bool scanBusy = false;
uint8_t sRow = 0, sCol = 0;
int panNow = PAN_CENTER;

// ---- timers ----
uint32_t startedAt, until_, enteredAt, lastCmd, lastRead, lastLive, lastUs, lastSlow, lastDht, lastStatus, movedAt;
uint8_t avoidPhase = 0;

// =============================== motors ===============================
// The L298N loses about 2 V, so small gear motors often don't start at a low PWM: the car "ignores" the command.
// Any non-zero speed is raised to MOTOR_MIN_PWM, and a motor that starts or reverses gets a short full-power kick.
int lastL = 0, lastR = 0;
int shaped(int v) {
  v = constrain(v, -255, 255);
  if (v && abs(v) < MOTOR_MIN_PWM) v = v > 0 ? MOTOR_MIN_PWM : -MOTOR_MIN_PWM;
  return v;
}
void side(uint8_t a, uint8_t b, uint8_t en, int v) {
  digitalWrite(a, v > 0);
  digitalWrite(b, v < 0);
  analogWrite(en, abs(v));
}
bool starts(int from, int to) { return to && (from == 0 || (from > 0) != (to > 0)); }
void drive(int l, int r) {
  l = shaped(l); r = shaped(r);
  if (MOTOR_KICK_MS && (starts(lastL, l) || starts(lastR, r))) {
    side(PIN_IN1, PIN_IN2, PIN_ENA, l ? (l > 0 ? 255 : -255) : 0);
    side(PIN_IN3, PIN_IN4, PIN_ENB, r ? (r > 0 ? 255 : -255) : 0);
    delay(MOTOR_KICK_MS);
  }
  side(PIN_IN1, PIN_IN2, PIN_ENA, l); side(PIN_IN3, PIN_IN4, PIN_ENB, r);
  lastL = l; lastR = r;
  moving = l || r;
}
void stopMotors() { drive(0, 0); }

// =============================== drill (12 V gear motor through a MOSFET on PIN_DRILL) ===============================
// Hold-to-run only: it needs a fresh "R,1" at least every DRILL_TIMEOUT_MS, runs only in manual mode,
// stops on E-STOP / Auto / alerts, and never longer than DRILL_MAX_MS in one go.
bool drilling = false;
uint32_t drillCmdAt = 0, drillStartAt = 0;
void drill(bool on) {
  if (on && !drilling) drillStartAt = millis();
  drilling = on;
  digitalWrite(PIN_DRILL, on != DRILL_ACTIVE_LOW);
}
void drillWatch() {
  if (!drilling) return;
  uint32_t now = millis();
  if (mode != MODE_MANUAL || now - drillCmdAt > DRILL_TIMEOUT_MS || now - drillStartAt > DRILL_MAX_MS) drill(false);
}

// =============================== MLX90614 (raw SMBus read) ===============================
bool mlxRead(uint8_t reg, float &out) {
  Wire.beginTransmission(0x5A);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((uint8_t)0x5A, (uint8_t)3) != 3) return false;
  uint16_t lo = Wire.read(), hi = Wire.read();
  Wire.read();                                  // PEC
  uint16_t raw = (hi << 8) | lo;
  if (raw & 0x8000) return false;
  out = raw * 0.02f - 273.15f;
  return true;
}
bool mlxTry(uint8_t reg, float &out) {        // one retry: a single disturbed read is common next to motors
  if (mlxRead(reg, out)) return true;
  if (Wire.getWireTimeoutFlag()) Wire.clearWireTimeoutFlag();
  delayMicroseconds(500);
  return mlxRead(reg, out);
}
uint8_t mlxFails = 0;
float mlxObject() {                   // "not responding" only after 3 failed reads in a row, not on one glitch
  float t;
  bool ok = mlxTry(0x07, t);
  mlxFails = ok ? 0 : min(mlxFails + 1, 10);
  thermalOk = mlxFails < 3;
  return ok ? t : NAN;
}

// =============================== thermal sweep ===============================
int colAngle(int c) { return PAN_MIN + c * PAN_STEP; }
int cellCol() { return (sRow % 2) ? SCAN_COLS - 1 - sCol : sCol; }   // serpentine path
uint32_t servoAt = 0;                // last time the head was moved
void aim(int pan, int tilt) {
  panServo.write(pan); tiltServo.write(tilt);          // value first, then power: no jump to the middle
  if (!panServo.attached()) panServo.attach(PIN_SERVO_PAN, 500, 2400);
  if (!tiltServo.attached()) tiltServo.attach(PIN_SERVO_TILT, 500, 2400);
  panNow = pan; servoAt = millis();
}
void servoRest() {                   // a holding SG90 hunts and buzzes; switched off it stays put (gears hold it)
  if (SERVO_IDLE_MS && !scanBusy && panServo.attached() && millis() - servoAt > SERVO_IDLE_MS) {
    panServo.detach(); tiltServo.detach();
  }
}
void centerHead() { aim(PAN_CENTER, TILT_ANGLES[TILT_ROWS - 1]); }

void startScan() {
  stopMotors();
  scanBusy = true; sRow = 0; sCol = 0;
  aim(colAngle(0), TILT_ANGLES[0]);
  movedAt = millis() + 250;
  state = A_SCAN;
}

bool scanStep() {                    // true when the sweep is finished
  if (!scanBusy) return true;
  if ((long)(millis() - movedAt) < SCAN_SETTLE_MS) return false;
  float a = mlxObject(), b = mlxObject();
  work[sRow][cellCol()] = isnan(a) ? b : (isnan(b) ? a : (a + b) / 2);
  if (++sCol >= SCAN_COLS) { sCol = 0; sRow++; }
  if (sRow >= TILT_ROWS) {
    memcpy(grid, work, sizeof(grid));
    scanCount++;
    scanBusy = false;
    centerHead();
    return true;
  }
  aim(colAngle(cellCol()), TILT_ANGLES[sRow]);
  movedAt = millis();
  return false;
}

int scanProgress() { return scanBusy ? (sRow * SCAN_COLS + sCol) * 100 / (TILT_ROWS * SCAN_COLS) : 100; }

// =============================== sensors ===============================
float readDistance() {
  digitalWrite(PIN_US_TRIG, LOW);  delayMicroseconds(2);
  digitalWrite(PIN_US_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(PIN_US_TRIG, LOW);
  unsigned long us = pulseIn(PIN_US_ECHO, HIGH, 25000UL);
  return us == 0 ? 400 : us / 58.0f;
}
bool pirReady() { return millis() - startedAt > PIR_WARMUP_MS; }
bool gasAlarm() { return gasRaw >= GAS_ALARM_RAW; }
// A reading outside 5.5-9 V can't be a working 2S pack: the divider is missing, loose or on the 5 V rail.
// Then the voltage is unknown (shown as n/a) and never stops the robot - before, a floating A1 read ~2 V = "battery low".
bool batteryKnown() { return BATTERY_MONITOR && batteryV >= 5.5f && batteryV <= 9.0f; }
bool batteryLow() { return batteryKnown() && batteryV < BATTERY_LOW_V; }
int batteryPct() { return constrain((int)((batteryV - 6.4f) / (8.4f - 6.4f) * 100), 0, 100); }

void updateSensors() {
  uint32_t now = millis();
  if (now - lastUs >= 60) {                         // median of the last 3 echoes: one bad echo can't stop the car
    lastUs = now;
    static float e[3] = {400, 400, 400};
    static uint8_t k = 0;
    e[k] = readDistance(); k = (k + 1) % 3;
    distanceCm = max(min(e[0], e[1]), min(max(e[0], e[1]), e[2]));
  }
  if (now - lastSlow >= 250) {
    lastSlow = now;
    gasRaw = (gasRaw * 3 + analogRead(PIN_GAS)) / 4;
#if BATTERY_MONITOR
    float v = analogRead(PIN_BATTERY) * (5.0f / 1023.0f) * BATTERY_DIVIDER * BATTERY_ADC_CAL;
    batteryV = batteryV < 1 ? v : batteryV * 0.9f + v * 0.1f;
#endif
  }
  if (!scanBusy && now - lastLive > 400) {          // live reading straight ahead for the dashboard
    lastLive = now;
    lastObject = mlxObject();
    float t;
    if (mlxRead(0x06, t)) ambient = t;
  }
  // The DHT11 read switches interrupts off for ~25 ms, and bytes from the camera board arriving then are lost.
  // That used to eat drive commands, so it is never read during a sweep or while driving / just after a command.
  bool busyLink = moving || drilling || now - lastCmd < 3000;
  if (!scanBusy && !busyLink && now - lastDht > DHT_EVERY_MS) {
    lastDht = now;
    float h = dht.readHumidity(), t = dht.readTemperature();
    dhtOk = !isnan(h) && !isnan(t);
    if (dhtOk) { humidity = h; airTemp = t; }
  }
  motion = pirReady() && digitalRead(PIN_PIR);
}

// =============================== outputs ===============================
bool headlight = false;              // car LED switched on from the dashboard
bool buzzing = false;
void buzzer(bool on) {
  if (on == buzzing) return;
  buzzing = on;
  if (BUZZER_PASSIVE) { if (on) tone(PIN_BUZZER, BUZZER_TONE_HZ); else noTone(PIN_BUZZER); }
  else digitalWrite(PIN_BUZZER, on != BUZZER_ACTIVE_LOW);
}
void beacon(bool on) { digitalWrite(PIN_LIGHT, on); }
void chirp(int ms) { buzzer(true); delay(ms); buzzer(false); }
void alertPattern(bool active) {
  if (!active) { if (patternOn) { buzzer(false); beacon(headlight); patternOn = false; } return; }
  patternOn = true;
  uint16_t t = millis() % 2000;
  buzzer(t < 150 || (t > 300 && t < 450) || (t > 600 && t < 750));
  beacon((t / 125) % 2);
}

// =============================== events (to the camera board) ===============================
void evStart(const __FlashStringHelper *kind, int s) {
  Serial.print(F("E,")); Serial.print(kind); Serial.print(','); Serial.print(s); Serial.print(',');
}
void event(const __FlashStringHelper *kind, const __FlashStringHelper *text, int s = 0) {
  evStart(kind, s); Serial.println(text);
}

// =============================== robot logic ===============================
void enter(AutoState s, uint32_t forMs) { state = s; enteredAt = millis(); until_ = enteredAt + forMs; }

void turnAway() { drive(-DRIVE_SPEED, -DRIVE_SPEED); avoidPhase = 0; enter(A_AVOID, 500); }
void avoidObstacle() { drive(-DRIVE_SPEED, -DRIVE_SPEED); avoidPhase = 0; enter(A_AVOID, 400); }

void setMode(Mode m) {
  stopMotors();
  drill(false);
  alertPattern(false);
  mode = m;
  state = A_IDLE;
  if (m == MODE_AUTO) {
    if (batteryLow()) { mode = MODE_MANUAL; event(F("hazard"), F("Battery low - search not started")); return; }
    startScan();
    event(F("info"), F("Autonomous search started"));
  } else if (m == MODE_ESTOP) {
    scanBusy = false;
    event(F("info"), F("EMERGENCY STOP"));
  }
}

void afterScan(bool autoMode) {
  finding = analyzeSweep(&grid[0][0], TILT_ROWS, SCAN_COLS);
  if (finding.fire) {
    evStart(F("hazard"), 0);
    Serial.print(F("Hot spot ")); Serial.print(finding.hottest, 0); Serial.println(F(" C - possible fire"));
  }
  if (finding.found) {
    score = confidenceScore(finding, NAN, false);
    int bearing = (int)lroundf(finding.panAngle - PAN_CENTER);     // + = left of the robot
    evStart(F("heat"), score);
    Serial.print(F("Heat signature ")); Serial.print(finding.peak, 1);
    Serial.print(F(" C (+")); Serial.print(finding.delta, 1); Serial.print(F(") at "));
    Serial.print(abs(bearing)); Serial.println(bearing >= 0 ? F(" deg left") : F(" deg right"));
  } else {
    score = 0;
  }
  if (!autoMode) { state = A_IDLE; return; }
  if (finding.found) {
    float turn = (finding.panAngle - PAN_CENTER) * TURN_SIGN;
    uint32_t ms = (uint32_t)(fabs(turn) / TURN_DEG_PER_SEC * 1000);
    if (turn > 0) drive(-TURN_SPEED, TURN_SPEED); else drive(TURN_SPEED, -TURN_SPEED);
    enter(A_ALIGN, ms);
  } else {
    enter(A_CRUISE, CRUISE_MS);
  }
}

void decide() {
  score = confidenceScore(finding, closeReading, motionSeen);
  if (score >= ALERT_SCORE) {
    survivors++;
    evStart(F("survivor"), score);
    Serial.print(F("SURVIVOR LIKELY - "));
    Serial.print(motionSeen ? F("moving") : F("NOT moving (may be unconscious)"));
    Serial.print(F(", ")); Serial.print(closeReading, 1); Serial.print(F(" C at "));
    Serial.print(distanceCm, 0); Serial.println(F(" cm"));
    state = A_ALERT;
    drill(false);
  } else if (score >= POSSIBLE_SCORE) {
    evStart(F("possible"), score);
    Serial.print(F("Possible survivor, check manually (")); Serial.print(closeReading, 1); Serial.println(F(" C)"));
    turnAway();
  } else {
    event(F("info"), F("Heat source rejected (not body-like)"), score);
    turnAway();
  }
}

void trackClose(uint16_t every) {
  if (millis() - lastRead > every) {
    lastRead = millis();
    lastObject = mlxObject();
    if (!isnan(lastObject) && (isnan(closeReading) || lastObject > closeReading)) closeReading = lastObject;
  }
}

void updateRobot() {
  uint32_t now = millis();
  if (gasAlarm() != gasWas) {
    gasWas = gasAlarm();
    if (gasWas) event(F("hazard"), F("Smoke / gas detected - rescuers use breathing protection"));
  }
  if (mode == MODE_ESTOP) { stopMotors(); drill(false); return; }
  if (mode == MODE_MANUAL) {
    if (moving && now - lastCmd > MANUAL_TIMEOUT_MS) stopMotors();     // dead-man
    if (scanBusy && scanStep()) afterScan(false);
    return;
  }
  if (batteryLow()) { setMode(MODE_MANUAL); event(F("hazard"), F("Battery low - search stopped")); return; }

  switch (state) {
    case A_SCAN:
      if (scanStep()) afterScan(true);
      break;
    case A_ALIGN:
      if ((long)(now - until_) >= 0) {
        stopMotors();
        aim(PAN_CENTER, TILT_ANGLES[finding.row]);
        closeReading = NAN;
        enter(A_APPROACH, 4000);
      }
      break;
    case A_APPROACH:
      trackClose(200);
      if (distanceCm <= APPROACH_STOP_CM || (long)(now - until_) >= 0) {
        stopMotors();
        motionSeen = false;
        enter(A_CONFIRM, CONFIRM_MS + 1000);
      } else {
        drive(CRAWL_SPEED, CRAWL_SPEED);
      }
      break;
    case A_CONFIRM:
      if (now - enteredAt > 1000 && motion) motionSeen = true;
      trackClose(300);
      if ((long)(now - until_) >= 0) decide();
      break;
    case A_ALERT:
      alertPattern(true);             // stays as a beacon until acknowledged
      break;
    case A_CRUISE:
      if (distanceCm < OBSTACLE_CM) { avoidObstacle(); break; }
      drive(DRIVE_SPEED, DRIVE_SPEED);
      if ((long)(now - until_) >= 0) startScan();
      break;
    case A_AVOID:
      if ((long)(now - until_) >= 0) {
        if (avoidPhase == 0) {
          avoidPhase = 1;
          if (random(2)) drive(-TURN_SPEED, TURN_SPEED); else drive(TURN_SPEED, -TURN_SPEED);
          until_ = now + 500 + random(500);
        } else {
          stopMotors();
          enter(A_CRUISE, CRUISE_MS);
        }
      }
      break;
    default:
      break;
  }
}

// =============================== link: commands from the camera board ===============================
char cmd[24];
uint8_t cmdLen = 0;
uint16_t rxOk = 0, rxBad = 0;        // commands received / rejected, shown on the dashboard

bool checked(char *c) {              // "D,180,180*5F": XOR of everything before '*', two hex digits
  char *star = strrchr(c, '*');
  if (!star || strlen(star) != 3) return false;
  uint8_t x = 0;
  for (char *p = c; p < star; p++) x ^= (uint8_t)*p;
  bool ok = x == (uint8_t)strtol(star + 1, nullptr, 16);
  *star = 0;
  return ok;
}

void handleCommand(char *c) {
  if (c[0] == 'D' && c[1] == ',') {
    int l = 0, r = 0;
    if (sscanf(c + 2, "%d,%d", &l, &r) == 2 && mode == MODE_MANUAL) {
      blocked = l > 0 && r > 0 && distanceCm < MANUAL_BLOCK_CM;      // don't ram anything
      if (blocked) l = r = 0;
      drive(l, r);
      lastCmd = millis();
    }
  } else if (c[0] == 'M' && c[1] == ',') {
    Mode m = !strcmp(c + 2, "auto") ? MODE_AUTO : !strcmp(c + 2, "estop") ? MODE_ESTOP : MODE_MANUAL;
    if (m != mode || m == MODE_ESTOP) setMode(m);
  } else if (c[0] == 'C') {
    if (mode == MODE_MANUAL && !scanBusy) { startScan(); state = A_IDLE; }
  } else if (c[0] == 'A') {
    if (state == A_ALERT) { alertPattern(false); event(F("info"), F("Alert acknowledged, search resumed"), score); turnAway(); }
  } else if (c[0] == 'B') {
    chirp(150);
  } else if (c[0] == 'R' && c[1] == ',') {                            // R,1 / R,0 = drill (held button)
    if (c[2] == '1' && mode == MODE_MANUAL) { drillCmdAt = millis(); if (!drilling) drill(true); }
    else drill(false);
    lastCmd = millis();
  } else if (c[0] == 'L' && c[1] == ',') {                            // L,1 / L,0 = car LED on / off
    headlight = c[2] == '1';
    if (!patternOn) beacon(headlight);
  }
}

void readLink() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (cmdLen) {
        cmd[cmdLen] = 0;
        if (checked(cmd)) { rxOk++; handleCommand(cmd); } else rxBad++;
        cmdLen = 0;
      }
    } else if (cmdLen < sizeof(cmd) - 1) {
      cmd[cmdLen++] = ch;
    } else {
      cmdLen = 0;                    // garbage line: drop it
    }
  }
}

// =============================== link: status to the camera board ===============================
void key(const __FlashStringHelper *k) { Serial.print('"'); Serial.print(k); Serial.print(F("\":")); }
void num(const __FlashStringHelper *k, float v, uint8_t d) { key(k); if (isnan(v)) Serial.print(F("null")); else Serial.print(v, d); Serial.print(','); }
void flagv(const __FlashStringHelper *k, bool b) { key(k); Serial.print(b ? F("true") : F("false")); Serial.print(','); }

void sendStatus() {
  Serial.print(F("S{"));
  key(F("mode")); Serial.print('"'); Serial.print(MODE_NAMES[mode]); Serial.print(F("\","));
  key(F("state")); Serial.print('"');
  if (mode == MODE_MANUAL) Serial.print(scanBusy ? F("scanning") : F("manual control"));
  else if (mode == MODE_ESTOP) Serial.print(F("STOPPED"));
  else Serial.print(STATE_NAMES[state]);
  Serial.print(F("\","));
  num(F("uptime"), millis() / 1000UL, 0);
  num(F("object"), lastObject, 1);
  num(F("ambient"), ambient, 1);
  num(F("airTemp"), airTemp, 1);
  num(F("humidity"), humidity, 0);
  num(F("distance"), distanceCm, 0);
  num(F("gas"), gasRaw, 0);
  num(F("battery"), batteryKnown() ? batteryV : 0, 2);
  num(F("batteryPct"), batteryPct(), 0);
  num(F("score"), score, 0);
  num(F("scanProgress"), scanProgress(), 0);
  num(F("pan"), panNow, 0);
  flagv(F("motion"), motion);
  flagv(F("pirReady"), pirReady());
  flagv(F("gasAlarm"), gasAlarm());
  flagv(F("batteryLow"), batteryLow());
  flagv(F("thermalOk"), thermalOk);
  flagv(F("dhtOk"), dhtOk);
  flagv(F("headlight"), headlight);
  flagv(F("moving"), moving);
  flagv(F("drill"), drilling);
  num(F("rx"), rxOk, 0);
  num(F("rxBad"), rxBad, 0);
  flagv(F("blocked"), blocked && millis() - lastCmd < 1000);
  flagv(F("alert"), state == A_ALERT && mode == MODE_AUTO);
  num(F("survivors"), survivors, 0);
  num(F("scans"), scanCount, 0);
  key(F("finding")); Serial.print('{');
  flagv(F("found"), finding.found);
  flagv(F("fire"), finding.fire);
  num(F("background"), finding.background, 1);
  num(F("peak"), finding.peak, 1);
  num(F("delta"), finding.delta, 1);
  num(F("bearing"), finding.panAngle - PAN_CENTER, 0);
  key(F("cells")); Serial.print(finding.cells); Serial.print(F("},"));
  key(F("grid")); Serial.print(F("{\"panMin\":")); Serial.print(PAN_MIN);
  Serial.print(F(",\"panStep\":")); Serial.print(PAN_STEP); Serial.print(F(",\"rows\":["));
  for (int y = 0; y < TILT_ROWS; y++) {
    Serial.print(y ? F(",[") : F("["));
    for (int x = 0; x < SCAN_COLS; x++) {
      if (x) Serial.print(',');
      if (isnan(grid[y][x])) Serial.print(F("null")); else Serial.print(grid[y][x], 1);
    }
    Serial.print(']');
  }
  Serial.println(F("]}}"));
}

// Scans the I2C bus and says what it found, so the log tells a wiring fault from a wrong address or a dead sensor.
void i2cReport() {
  uint8_t found[4], n = 0;
  for (uint8_t a = 1; a < 127 && n < 4; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) found[n++] = a;
  }
  evStart(F("hazard"), 0);
  if (!n) { Serial.println(F("No I2C device on A4/A5: check SDA, SCL, VIN, GND of the GY-906")); return; }
  Serial.print(F("Thermal sensor not at 0x5A. I2C found:"));
  for (uint8_t i = 0; i < n; i++) { Serial.print(F(" 0x")); Serial.print(found[i], HEX); }
  Serial.println();
}

// =============================== setup / loop ===============================
void setup() {
  Serial.begin(LINK_BAUD);
  pinMode(PIN_DRILL, OUTPUT); drill(false);            // drill off first, before anything else
  uint8_t outs[] = {PIN_IN1, PIN_IN2, PIN_IN3, PIN_IN4, PIN_ENA, PIN_ENB, PIN_BUZZER, PIN_LIGHT, PIN_US_TRIG};
  for (uint8_t p : outs) { pinMode(p, OUTPUT); digitalWrite(p, LOW); }
  buzzing = true; buzzer(false);                       // silent at start, also for low-trigger modules
  pinMode(PIN_US_ECHO, INPUT);
  pinMode(PIN_PIR, INPUT);
  for (auto &row : grid) for (float &c : row) c = NAN;
  pinMode(A5, OUTPUT); digitalWrite(A5, LOW); delay(3); pinMode(A5, INPUT);  // SCL low >1.44 ms: an MLX90614
                                                       // that shipped in PWM mode switches to I2C (SMBus)
  Wire.begin();
  Wire.setClock(100000);
  Wire.setWireTimeout(5000, true);  // a disturbed I2C bus used to hang the Uno for good: no commands, motors stuck
  centerHead();                                        // attaches the servos; they rest after SERVO_IDLE_MS
  dht.begin();
  randomSeed(analogRead(PIN_GAS) ^ micros());
  startedAt = millis();
  delay(300);                                          // the MLX90614 needs ~250 ms after power-up
  float t;
  thermalOk = mlxTry(0x06, t);
  if (thermalOk) event(F("info"), F("Robot ready, thermal sensor OK"));
  else i2cReport();
  chirp(60); delay(80); chirp(60);                     // two short beeps = ready
}

void loop() {
  readLink();
  updateSensors();
  updateRobot();
  drillWatch();
  servoRest();
  if (millis() - lastStatus >= (moving || drilling ? STATUS_DRIVING_MS : STATUS_EVERY_MS)) { lastStatus = millis(); sendStatus(); }
}
