// ResQBot Mini - Arduino Uno main board: all pins and tuning values.
// The Uno reads every sensor, drives the robot and sends its status to the ESP32-CAM over Serial (D0/D1).
#pragma once

// ---------------- Link to the ESP32-CAM (hardware Serial on D0/D1) ----------------------
#define LINK_BAUD        115200
#define STATUS_EVERY_MS  400     // status line to the camera board
#define STATUS_DRIVING_MS 900    // slower while driving: printing the long status line holds up the Uno's loop
// D1 (TX) -> 1k/2k divider -> ESP32-CAM GPIO13 ; ESP32-CAM GPIO14 -> D0 (RX)
// Unplug the D0 wire (or switch the robot off) while uploading code to the Uno.

// ---------------- Motor driver L298N -------------------------------------------------------
#define PIN_ENA   5    // left motors speed (PWM)
#define PIN_ENB   6    // right motors speed (PWM)
#define PIN_IN1   7
#define PIN_IN2   8
#define PIN_IN3   9
#define PIN_IN4   10

// ---------------- Thermal head: MLX90614 on I2C (A4 SDA, A5 SCL) + two servos ---------------
#define PIN_SERVO_PAN  11
#define PIN_SERVO_TILT 12
#define SERVO_IDLE_MS  700     // servos are switched off this long after their last move: no buzzing or shaking
                               // while they just hold still (set 0 to keep them powered all the time)

// ---------------- Other sensors and outputs ------------------------------------------------
#define PIN_DHT      2    // DHT11 data (air temperature and humidity)
#define PIN_BUZZER   3    // 5 V buzzer MODULE signal pin (I/O or S). Module VCC -> 5V, GND -> GND. No transistor needed.
#define BUZZER_ACTIVE_LOW false   // true if your module beeps when the pin is LOW: it then beeps nonstop after
                                  // power-on and is silent on "Beep". Modules with an S8550 transistor are often LOW.
#define BUZZER_PASSIVE    false   // true if your module only clicks: a passive buzzer needs a tone
#define BUZZER_TONE_HZ    2700
#define PIN_PIR      4    // HC-SR501 output
#define PIN_LIGHT    13   // car LED: + (long leg) -> 220 ohm resistor -> D13, - (short leg) -> GND
                          // headlight button on the dashboard; blinks as a beacon during a survivor alert
#define PIN_GAS      A0   // MQ-2 analog out (0-5 V, direct)
#define PIN_BATTERY  A1   // only used when BATTERY_MONITOR is true (A1 is the drill now)

// ---------------- Drill: 12 V gear motor switched by a MOSFET (low side) --------------------
// Every Uno pin was taken, so the drill uses A1 (the old battery-divider pin): remove the divider wire from A1.
// MOSFET module: SIG -> A1, GND -> GND.  Bare IRLZ44N/IRFZ44N: A1 -> 220 ohm -> gate, 10k gate -> GND.
// Motor + -> 12 V, motor - -> MOSFET drain (module V-/OUT-), 12 V GND = Uno GND. Diode across the motor (stripe to +).
#define PIN_DRILL          A1
#define DRILL_ACTIVE_LOW   false   // true only if your driver board switches ON when its input is LOW
#define DRILL_TIMEOUT_MS   600     // dead-man: the drill stops if the phone stops holding the button
#define DRILL_MAX_MS       30000   // never runs longer than this in one go (lift the finger and press again)
#define PIN_US_TRIG  A2   // HC-SR04 trigger
#define PIN_US_ECHO  A3   // HC-SR04 echo (5 V, direct)

// ---------------- Driving --------------------------------------------------------------------
#define DRIVE_SPEED        170
#define TURN_SPEED         180
#define CRAWL_SPEED        150     // slow approach to a person (not below MOTOR_MIN_PWM)
#define TURN_DEG_PER_SEC   120.0   // measure during calibration
#define TURN_SIGN          1       // -1 if in Auto search the robot turns AWAY from the heat (pan servo mounted the other way)
#define MANUAL_TIMEOUT_MS  800     // dead-man: stop if the phone stops sending drive commands (sent every 150 ms)
#define MANUAL_BLOCK_CM    10      // manual forward is refused when an obstacle is this close (0 = never block)
#define MOTOR_MIN_PWM      150     // lowest speed actually sent: below this BO motors behind an L298N often stall
#define MOTOR_KICK_MS      60      // full-power kick when a motor starts or reverses (0 = off)

// ---------------- Obstacles ----------------------------------------------------------------
#define OBSTACLE_CM        25
#define APPROACH_STOP_CM   35
#define CRUISE_MS          2500

// ---------------- Thermal sweep ------------------------------------------------------------
#define PAN_MIN        20
#define PAN_MAX        160
#define PAN_STEP       10      // 15 columns
#define PAN_CENTER     90
#define TILT_ROWS      2
static const int TILT_ANGLES[TILT_ROWS] = {70, 95};   // floor, level
#define SCAN_SETTLE_MS 160

// ---------------- Survivor detection -------------------------------------------------------
#define DELTA_MIN_C      1.5
#define BODY_MAX_C       42.0
#define FIRE_C           55.0
#define MIN_BLOB_CELLS   2
#define CONFIRM_MS       5000
#define PIR_WARMUP_MS    30000
#define ALERT_SCORE      60
#define POSSIBLE_SCORE   35

// ---------------- Hazards, battery, DHT11 --------------------------------------------------
#define GAS_ALARM_RAW    400      // MQ-2 reading 0-1023; calibrate in clean air (+40 %)
#define BATTERY_MONITOR  false    // A1 drives the drill now; true only if the drill is moved off A1
#define BATTERY_DIVIDER  2.0      // 10k / 10k
#define BATTERY_LOW_V    6.8
#define BATTERY_ADC_CAL  1.00
#define DHT_EVERY_MS     5000     // DHT11 is slow; read every 5 s, never during a sweep
