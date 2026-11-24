// Wi-Fi hotspot + phone dashboard. Open http://192.168.4.1 after joining the robot's Wi-Fi.
#pragma once
#include <WiFi.h>
#include <WebServer.h>
#include "robot.h"
#include "dashboard_html.h"

class Web {
 public:
  void begin(Robot &r) {
    robot_ = &r;
    WiFi.mode(WIFI_AP);
    WiFi.softAP(WIFI_SSID, WIFI_PASSWORD);
    Serial.printf("Wi-Fi \"%s\" password \"%s\" -> http://%s\n", WIFI_SSID, WIFI_PASSWORD,
                  WiFi.softAPIP().toString().c_str());

    server_.enableCORS(true);      // lets a phone app (other origin, e.g. a Capacitor APK) read the API
    server_.on("/", [this] { server_.send_P(200, "text/html", DASHBOARD_HTML); });
    server_.on("/api/info", [this] {
      server_.send(200, "application/json",
                   "{\"name\":\"" WIFI_SSID "\",\"firmware\":\"1.0\",\"camera\":\"" CAM_URL "\"}");
    });
    server_.on("/api/status", [this] { status(); });
    server_.on("/api/drive", [this] { drive(); });
    server_.on("/api/mode", [this] { mode(); });
    server_.on("/api/scan", [this] { robot_->requestScan(); ok(); });
    server_.on("/api/ack", [this] { robot_->acknowledge(); ok(); });
    server_.on("/api/beep", [this] { robot_->sensors.chirp(150); ok(); });
    server_.on("/api/log.csv", [this] { csv(); });
    server_.onNotFound([this] { server_.send(404, "text/plain", "not found"); });
    server_.begin();
  }

  void update() { server_.handleClient(); }

 private:
  WebServer server_{80};
  Robot *robot_ = nullptr;

  void ok() { server_.send(200, "application/json", "{\"ok\":true}"); }

  // /api/drive?l=-255..255&r=-255..255   (sent every 200 ms while a button is held)
  void drive() {
    robot_->manualDrive(server_.arg("l").toInt(), server_.arg("r").toInt());
    ok();
  }

  // /api/mode?m=manual|auto|estop
  void mode() {
    String m = server_.arg("m");
    robot_->setMode(m == "auto" ? MODE_AUTO : m == "estop" ? MODE_ESTOP : MODE_MANUAL);
    ok();
  }

  static void num(String &s, const char *key, float v, int digits = 1) {
    s += '"'; s += key; s += "\":";
    s += isnan(v) ? String("null") : String(v, digits);
    s += ',';
  }

  static void jsonText(String &s, const char *t) {
    s += '"';
    for (; *t; t++) { if (*t == '"' || *t == '\\') s += '\\'; s += *t; }
    s += '"';
  }

  void status() {
    Robot &r = *robot_;
    String s;
    s.reserve(2600);
    s += "{\"mode\":\""; s += MODE_NAMES[r.mode];
    s += "\",\"state\":\""; s += r.stateName();
    s += "\",\"camera\":\"" CAM_URL "\",";
    num(s, "uptime", millis() / 1000.0f, 0);
    num(s, "object", r.scanner.lastObject);
    num(s, "ambient", r.scanner.ambient);
    num(s, "distance", r.sensors.distanceCm, 0);
    num(s, "gas", r.sensors.gasRaw, 0);
    num(s, "battery", r.sensors.batteryV, 2);
    num(s, "batteryPct", r.sensors.batteryPct(), 0);
    num(s, "score", r.score, 0);
    num(s, "scanProgress", r.scanner.progress(), 0);
    num(s, "pan", r.scanner.panNow, 0);
    num(s, "clients", WiFi.softAPgetStationNum(), 0);
    s += "\"motion\":"; s += r.sensors.motion ? "true" : "false";
    s += ",\"pirReady\":"; s += r.sensors.pirReady() ? "true" : "false";
    s += ",\"gasAlarm\":"; s += r.sensors.gasAlarm() ? "true" : "false";
    s += ",\"batteryLow\":"; s += r.sensors.batteryLow() ? "true" : "false";
    s += ",\"thermalOk\":"; s += r.thermalOk ? "true" : "false";
    s += ",\"alert\":"; s += r.state == A_ALERT && r.mode == MODE_AUTO ? "true" : "false";
    s += ",\"survivors\":"; s += r.survivors;
    s += ",\"scans\":"; s += r.scanner.scanCount;

    const Finding &f = r.finding;
    s += ",\"finding\":{\"found\":"; s += f.found ? "true" : "false";
    s += ",\"fire\":"; s += f.fire ? "true" : "false"; s += ',';
    num(s, "background", f.background);
    num(s, "peak", f.peak);
    num(s, "delta", f.delta);
    num(s, "bearing", f.panAngle - PAN_CENTER, 0);
    s += "\"cells\":"; s += f.cells; s += '}';

    s += ",\"grid\":{\"panMin\":"; s += PAN_MIN; s += ",\"panStep\":"; s += PAN_STEP; s += ",\"rows\":[";
    for (int y = 0; y < TILT_ROWS; y++) {
      s += y ? ",[" : "[";
      for (int x = 0; x < SCAN_COLS; x++) {
        if (x) s += ',';
        float v = r.scanner.grid[y][x];
        s += isnan(v) ? String("null") : String(v, 1);
      }
      s += ']';
    }
    s += "]}";

    s += ",\"events\":[";                   // newest first, max 10
    int n = min(r.logCount, 10);
    for (int i = 0; i < n; i++) {
      const Event &e = r.log[(r.logCount - 1 - i) % Robot::LOG_SIZE];
      s += i ? ",{" : "{";
      s += "\"t\":"; s += e.ms / 1000; s += ",\"kind\":\""; s += e.kind; s += "\",\"text\":";
      jsonText(s, e.text);
      s += ",\"score\":"; s += e.score; s += '}';
    }
    s += "]}";
    server_.send(200, "application/json", s);
  }

  void csv() {
    Robot &r = *robot_;
    String s = "seconds,kind,confidence,text\n";
    int n = min(r.logCount, Robot::LOG_SIZE);
    for (int i = n - 1; i >= 0; i--) {
      const Event &e = r.log[(r.logCount - 1 - i) % Robot::LOG_SIZE];
      s += String(e.ms / 1000.0, 1) + "," + e.kind + "," + e.score + ",\"" + e.text + "\"\n";
    }
    server_.sendHeader("Content-Disposition", "attachment; filename=resqbot_log.csv");
    server_.send(200, "text/csv", s);
  }
};
