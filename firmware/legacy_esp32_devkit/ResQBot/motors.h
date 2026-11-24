// Two-channel drive through an L298N: left pair on A, right pair on B.
#pragma once
#include <Arduino.h>
#include "config.h"

class Motors {
 public:
  void begin() {
    int pins[] = {PIN_IN1, PIN_IN2, PIN_IN3, PIN_IN4};
    for (int p : pins) { pinMode(p, OUTPUT); digitalWrite(p, LOW); }
#if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcAttach(PIN_ENA, 1000, 8);
    ledcAttach(PIN_ENB, 1000, 8);
#else
    ledcSetup(0, 1000, 8); ledcAttachPin(PIN_ENA, 0);
    ledcSetup(1, 1000, 8); ledcAttachPin(PIN_ENB, 1);
#endif
    stop();
  }

  // left/right: -255 (full reverse) .. 255 (full forward)
  void drive(int left, int right) {
    side(PIN_IN1, PIN_IN2, PIN_ENA, 0, left);
    side(PIN_IN3, PIN_IN4, PIN_ENB, 1, right);
    moving_ = left != 0 || right != 0;
  }

  void forward(int s)   { drive(s, s); }
  void backward(int s)  { drive(-s, -s); }
  void turnLeft(int s)  { drive(-s, s); }   // spin on the spot
  void turnRight(int s) { drive(s, -s); }
  void stop()           { drive(0, 0); }
  bool moving() const   { return moving_; }

 private:
  bool moving_ = false;

  static void side(int a, int b, int en, int ch, int v) {
    v = constrain(v, -255, 255);
    digitalWrite(a, v > 0);
    digitalWrite(b, v < 0);
#if ESP_ARDUINO_VERSION_MAJOR >= 3
    (void)ch;
    ledcWrite(en, abs(v));
#else
    (void)en;
    ledcWrite(ch, abs(v));
#endif
  }
};
