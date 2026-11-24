// Ultrasonic distance, PIR motion, MQ-2 smoke/gas, battery voltage, buzzer and beacon.
#pragma once
#include <Arduino.h>
#include "config.h"

class Sensors {
 public:
  float distanceCm = 400;   // 400 = nothing in range
  bool motion = false;
  int gasRaw = 0;
  float batteryV = 0;

  void begin() {
    pinMode(PIN_US_TRIG, OUTPUT);
    pinMode(PIN_US_ECHO, INPUT);
    pinMode(PIN_PIR, INPUT);
    pinMode(PIN_BUZZER, OUTPUT);
    pinMode(PIN_BEACON, OUTPUT);
    analogSetPinAttenuation(PIN_GAS, ADC_11db);
    analogSetPinAttenuation(PIN_BATTERY, ADC_11db);
    startedAt_ = millis();
  }

  // Call often; each sensor has its own pace.
  void update() {
    uint32_t now = millis();
    if (now - lastUs_ >= 60) { lastUs_ = now; distanceCm = readDistance(); }
    if (now - lastSlow_ >= 250) {
      lastSlow_ = now;
      gasRaw = (gasRaw * 3 + analogRead(PIN_GAS)) / 4;   // light smoothing
      float v = analogReadMilliVolts(PIN_BATTERY) / 1000.0f * BATTERY_DIVIDER * BATTERY_ADC_CAL;
      batteryV = batteryV < 1 ? v : batteryV * 0.9f + v * 0.1f;
    }
    motion = pirReady() && digitalRead(PIN_PIR);
  }

  bool pirReady() const { return millis() - startedAt_ > PIR_WARMUP_MS; }
  bool gasAlarm() const { return gasRaw >= GAS_ALARM_RAW; }
  bool batteryLow() const { return batteryV > 1 && batteryV < BATTERY_LOW_V; }  // >1: battery sense wired
  int batteryPct() const { return constrain((int)((batteryV - 6.4f) / (8.4f - 6.4f) * 100), 0, 100); }

  // ---- outputs ----
  void beacon(bool on) { digitalWrite(PIN_BEACON, on); }
  void buzzer(bool on) { digitalWrite(PIN_BUZZER, on); }

  // Repeating pattern: 3 short beeps + flashing beacon (survivor alert), or silent.
  void alertPattern(bool active) {
    if (!active) { if (patternOn_) { buzzer(false); beacon(false); patternOn_ = false; } return; }
    patternOn_ = true;
    uint32_t t = millis() % 2000;
    bool beep = (t < 150) || (t > 300 && t < 450) || (t > 600 && t < 750);
    buzzer(beep);
    beacon((t / 125) % 2);
  }
  void chirp(int ms = 80) { buzzer(true); delay(ms); buzzer(false); }

 private:
  uint32_t lastUs_ = 0, lastSlow_ = 0, startedAt_ = 0;
  bool patternOn_ = false;

  static float readDistance() {
    digitalWrite(PIN_US_TRIG, LOW);  delayMicroseconds(2);
    digitalWrite(PIN_US_TRIG, HIGH); delayMicroseconds(10);
    digitalWrite(PIN_US_TRIG, LOW);
    unsigned long us = pulseIn(PIN_US_ECHO, HIGH, 25000);   // 25 ms = ~4 m, keeps the loop fast
    return us == 0 ? 400 : us / 58.0f;
  }
};
