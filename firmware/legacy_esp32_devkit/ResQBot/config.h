// ResQBot Mini - all pins and tuning values in one place.
// Board: ESP32 DevKit V1 (ESP32-WROOM-32), Arduino core 3.x.
#pragma once

// ---------------- Wi-Fi (the robot makes its own hotspot, no internet needed) -------------
#define WIFI_SSID        "ResQBot-01"       // the ESP32-CAM joins this network too (firmware/ResQCam)
#define WIFI_PASSWORD    "rescue123"        // at least 8 characters; change it in both sketches
#define CAM_URL          "http://192.168.4.50" // ESP32-CAM fixed address on the robot's Wi-Fi

// ---------------- Motor driver L298N -------------------------------------------------------
#define PIN_ENA   25   // left motors speed (PWM)
#define PIN_IN1   26
#define PIN_IN2   27
#define PIN_IN3   14
#define PIN_IN4   13
#define PIN_ENB   33   // right motors speed (PWM)

// ---------------- Thermal scanner (MLX90614 on a pan-tilt) --------------------------------
#define PIN_SDA        21
#define PIN_SCL        22
#define PIN_SERVO_PAN  18
#define PIN_SERVO_TILT 19

// ---------------- Other sensors and outputs ------------------------------------------------
#define PIN_US_TRIG  4    // HC-SR04 trigger
#define PIN_US_ECHO  16   // HC-SR04 echo, through a 1k/2k divider (5 V -> 3.3 V)
#define PIN_PIR      32   // HC-SR501 output (3.3 V logic)
#define PIN_GAS      34   // MQ-2 analog out, through a 10k/20k divider (ADC1 only: ADC2 is off while Wi-Fi runs)
#define PIN_BATTERY  35   // battery + through 100k/47k divider
#define PIN_BUZZER   23   // active buzzer through an NPN transistor
#define PIN_BEACON   2    // bright LED beacon (also the on-board blue LED)

// ---------------- Driving --------------------------------------------------------------------
#define DRIVE_SPEED        170   // 0-255 PWM for normal driving
#define TURN_SPEED         180   // PWM for turning on the spot
#define CRAWL_SPEED        130   // PWM while approaching a possible survivor
#define TURN_DEG_PER_SEC   120.0 // measured during calibration (see docs/BUILD_GUIDE.md)
#define MANUAL_TIMEOUT_MS  600   // dead-man: motors stop if the phone stops sending commands

// ---------------- Obstacles ----------------------------------------------------------------
#define OBSTACLE_CM        25    // turn away below this
#define APPROACH_STOP_CM   35    // stop this close to a heat source
#define CRUISE_MS          2500  // drive this long between thermal scans in search mode

// ---------------- Thermal sweep ------------------------------------------------------------
#define PAN_MIN        20     // degrees, robot's right
#define PAN_MAX        160    // degrees, robot's left
#define PAN_STEP       10     // 15 columns
#define PAN_CENTER     90
#define TILT_ROWS      2
static const int TILT_ANGLES[TILT_ROWS] = {70, 95};  // looking down at the floor, then level
#define SCAN_SETTLE_MS 160    // servo settle + sensor refresh per cell

// ---------------- Survivor detection -------------------------------------------------------
#define DELTA_MIN_C      1.5  // a cell must be this much warmer than the scene background
#define BODY_MAX_C       42.0 // warmer than this is not a person (heater, fire, engine)
#define FIRE_C           55.0 // hot-spot hazard warning
#define MIN_BLOB_CELLS   2    // a person covers at least 2 neighbouring cells
#define CONFIRM_MS       5000 // PIR watch time once stopped in front of the target
#define PIR_WARMUP_MS    30000// HC-SR501 gives false triggers for ~30 s after power-on
#define ALERT_SCORE      60   // confidence (0-100) for a "survivor likely" alert
#define POSSIBLE_SCORE   35   // confidence for a "possible survivor" report

// ---------------- Hazards and battery ------------------------------------------------------
#define GAS_ALARM_RAW    1800 // MQ-2 ADC reading (0-4095) treated as smoke/gas; calibrate in clean air
#define BATTERY_DIVIDER  (147.0 / 47.0)
#define BATTERY_LOW_V    6.8  // 2S Li-ion: stop autonomous search below this
#define BATTERY_ADC_CAL  1.00 // multiply to match a multimeter reading
