/*
  ResQBot - thermal sensor test (MLX90614 / GY-906) on its own.
  1. Unplug the D0 and D1 wires to the ESP32-CAM, plug the Uno into the laptop by USB.
  2. Upload this sketch, open Tools > Serial Monitor, set 115200 baud.
  3. Read what it prints every second (the meaning of each line is printed with it).
  Wiring: VIN -> 5V (or 3.3V), GND -> GND, SDA -> A4, SCL -> A5.
*/
#include <Wire.h>

void wakeSMBus() {
  // Some MLX90614 boards ship in PWM mode and then ignore I2C. Holding SCL low for >1.44 ms switches them to SMBus.
  pinMode(A5, OUTPUT);
  digitalWrite(A5, LOW);
  delay(3);
  pinMode(A5, INPUT);
}

bool readTemp(uint8_t reg, float &out, uint8_t &err) {
  Wire.beginTransmission(0x5A);
  Wire.write(reg);
  err = Wire.endTransmission(false);
  if (err) return false;
  if (Wire.requestFrom((uint8_t)0x5A, (uint8_t)3) != 3) { err = 9; return false; }
  uint16_t lo = Wire.read(), hi = Wire.read();
  Wire.read();
  out = ((hi << 8) | lo) * 0.02f - 273.15f;
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println(F("\n=== ResQBot thermal sensor test ==="));
  Serial.print(F("Voltage on A4 (SDA) and A5 (SCL), should both be HIGH (1): "));
  pinMode(A4, INPUT); pinMode(A5, INPUT);
  Serial.print(digitalRead(A4)); Serial.print(' '); Serial.println(digitalRead(A5));
  Serial.println(F("  0 on either = that wire is shorted to GND, or the board has no power / no pull-up resistors."));
  wakeSMBus();
  delay(300);
  Wire.begin();
  Wire.setClock(100000);
  Wire.setWireTimeout(5000, true);
}

void loop() {
  Serial.print(F("I2C scan: "));
  uint8_t n = 0;
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) { Serial.print(F("0x")); Serial.print(a, HEX); Serial.print(' '); n++; }
  }
  if (!n) Serial.print(F("NOTHING FOUND"));
  Serial.println();

  float obj, amb;
  uint8_t err;
  if (readTemp(0x07, obj, err) && readTemp(0x06, amb, err)) {
    Serial.print(F("  OK  object (what it points at) = ")); Serial.print(obj, 1);
    Serial.print(F(" C   sensor itself = ")); Serial.print(amb, 1); Serial.println(F(" C"));
    Serial.println(F("  -> The sensor works. Point it at your hand: object should rise to ~30-34 C."));
  } else {
    Serial.print(F("  FAILED to read 0x5A, error ")); Serial.println(err);
    if (!n) Serial.println(F("  -> Nothing on the bus: check VIN, GND, SDA->A4, SCL->A5 (swap SDA/SCL if unsure), loose jumpers."));
    else Serial.println(F("  -> Something answers but not at 0x5A: send the address shown above."));
  }
  delay(1000);
}
