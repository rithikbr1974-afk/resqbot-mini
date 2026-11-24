// MLX90614 infrared thermometer swept by a pan-tilt servo pair = a tiny 2 x 15 "thermal camera".
// The sensor is read directly over I2C (SMBus), so no extra library is needed for it.
#pragma once
#include <Arduino.h>
#include <Wire.h>
#include <ESP32Servo.h>
#include "config.h"

static const int SCAN_COLS = (PAN_MAX - PAN_MIN) / PAN_STEP + 1;

class MLX90614 {
 public:
  bool begin() {
    Wire.begin(PIN_SDA, PIN_SCL);
    Wire.setClock(100000);           // SMBus limit
    float t;
    ok_ = readReg(0x06, t);
    return ok_;
  }
  bool ok() const { return ok_; }
  // Object (what the sensor looks at) and ambient (sensor body) temperature in degC. NAN on error.
  float object()  { float t; ok_ = readReg(0x07, t); return ok_ ? t : NAN; }
  float ambient() { float t; return readReg(0x06, t) ? t : NAN; }

 private:
  bool ok_ = false;
  static bool readReg(uint8_t reg, float &out) {
    Wire.beginTransmission(0x5A);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;
    if (Wire.requestFrom((uint8_t)0x5A, (uint8_t)3) != 3) return false;
    uint16_t lo = Wire.read(), hi = Wire.read();
    Wire.read();                     // PEC byte, not checked
    uint16_t raw = (hi << 8) | lo;
    if (raw & 0x8000) return false;  // error flag
    out = raw * 0.02f - 273.15f;
    return true;
  }
};

class ThermalScanner {
 public:
  float grid[TILT_ROWS][SCAN_COLS];  // last finished sweep, degC
  float lastObject = NAN, ambient = NAN;
  uint32_t scanCount = 0;

  bool begin() {
    pan_.setPeriodHertz(50);
    tilt_.setPeriodHertz(50);
    pan_.attach(PIN_SERVO_PAN, 500, 2400);
    tilt_.attach(PIN_SERVO_TILT, 500, 2400);
    center();
    for (auto &row : grid) for (float &c : row) c = NAN;
    return mlx.begin();
  }

  void center() { aim(PAN_CENTER, TILT_ANGLES[TILT_ROWS - 1]); }
  void aim(int pan, int tilt) { pan_.write(pan); tilt_.write(tilt); panNow = pan; }

  // Start a sweep; call step() from loop() until it returns true (finished).
  void start() {
    busy_ = true; row_ = 0; col_ = 0;
    aim(colAngle(0), TILT_ANGLES[0]);
    movedAt_ = millis() + 250;       // first move is the longest
  }
  bool busy() const { return busy_; }
  int progress() const { return busy_ ? (row_ * SCAN_COLS + col_) * 100 / (TILT_ROWS * SCAN_COLS) : 100; }

  bool step() {
    if (!busy_) return true;
    if (millis() - movedAt_ < SCAN_SETTLE_MS) return false;
    float a = mlx.object(), b = mlx.object();
    work_[row_][cellCol()] = isnan(a) ? b : (isnan(b) ? a : (a + b) / 2);
    // serpentine path: right-to-left on one row, left-to-right on the next (no long servo jump)
    if (++col_ >= SCAN_COLS) { col_ = 0; row_++; }
    if (row_ >= TILT_ROWS) {
      memcpy(grid, work_, sizeof(grid));
      ambient = mlx.ambient();
      scanCount++;
      busy_ = false;
      center();
      return true;
    }
    aim(colAngle(cellCol()), TILT_ANGLES[row_]);
    movedAt_ = millis();
    return false;
  }

  // Quick single reading straight ahead (used while approaching / confirming).
  float readAhead() { lastObject = mlx.object(); return lastObject; }

  static int colAngle(int c) { return PAN_MIN + c * PAN_STEP; }
  int panNow = PAN_CENTER;
  MLX90614 mlx;

 private:
  Servo pan_, tilt_;
  float work_[TILT_ROWS][SCAN_COLS];
  bool busy_ = false;
  int row_ = 0, col_ = 0;
  uint32_t movedAt_ = 0;

  // grid column being measured; odd rows run backwards
  int cellCol() const { return (row_ % 2) ? SCAN_COLS - 1 - col_ : col_; }
};
