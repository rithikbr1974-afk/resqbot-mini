/*
  ResQBot Mini - low-cost thermal search-and-rescue rover
  ---------------------------------------------------------
  ESP32 + MLX90614 IR thermometer on a pan-tilt (a 2 x 15 "thermal camera"),
  HC-SR04 obstacle sensor, HC-SR501 PIR, MQ-2 smoke/gas sensor, L298N 4WD drive,
  plus an ESP32-CAM (firmware/ResQCam) streaming live video into the same dashboard.

  1. Join the Wi-Fi "ResQBot-01" (password in config.h) from a phone.
  2. Open http://192.168.4.1 - drive it, run a thermal scan, or start autonomous search.

  Libraries: ESP32Servo (Library Manager). Board: "ESP32 Dev Module", Arduino-ESP32 core 3.x.
  All pins and thresholds: config.h. Build guide: docs/BUILD_GUIDE.md.
*/
#include "config.h"
#include "robot.h"
#include "web.h"

Robot robot;
Web web;

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\nResQBot Mini starting");
  robot.begin();
  web.begin(robot);
  robot.sensors.chirp(60);   // two short beeps = ready
  delay(80);
  robot.sensors.chirp(60);
}

void loop() {
  web.update();
  robot.update();
}
