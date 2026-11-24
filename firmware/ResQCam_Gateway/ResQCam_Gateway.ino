/*
  ResQBot Mini - ESP32-CAM gateway (AI-Thinker ESP32-CAM + OV2640)
  -----------------------------------------------------------------
  - Makes the robot's own Wi-Fi hotspot "ResQBot-01" (no internet needed). Phone: http://192.168.4.1
  - Serves the dashboard and the JSON API, using the data the Arduino Uno sends over a serial link
  - Streams live video at the same time: http://192.168.4.1:81/stream  (its own server task)
  - Forwards the phone's drive / mode / scan / acknowledge / beep commands to the Uno
  - Fast control: drive and drill go over a WebSocket (ws://192.168.4.1/ws), with plain HTTP as a fallback.
    The gateway itself repeats the held command to the Uno every 100 ms and stops it 600 ms after the phone
    stops sending, so one lost byte or one slow Wi-Fi packet no longer swallows a button press.

  Serial link to the Uno (115200 baud):  ESP32-CAM GPIO13 (RX) <- 1k/2k divider <- Uno D1 (TX)
                                         ESP32-CAM GPIO14 (TX) -> Uno D0 (RX)
  GPIO13/14 are SD-card pins: leave the micro-SD slot empty.
  Board: "AI Thinker ESP32-CAM", Arduino-ESP32 core 3.x. Upload with the ESP32-CAM-MB board.
*/
#include "esp_camera.h"
#include "esp_http_server.h"
#include <WiFi.h>
#include "dashboard_html.h"

#define WIFI_SSID     "ResQBot-01"
#define WIFI_PASSWORD "rescue123"        // at least 8 characters
#define WIFI_CHANNEL  6                  // try 1 or 11 if many other Wi-Fi networks are around
#define CAM_URL       "http://192.168.4.1"
#define MAX_VIEWERS   2                  // phones that can watch the video at once (a 3rd takes over the oldest)
#define FRAME_MS      70                 // at most ~14 video frames a second per phone: leaves Wi-Fi time for the controls
#define LINK_RX 13
#define LINK_TX 14
#define FLASH_LED 4
// The on-board flash LED is a 1 W LED with almost no cooling. At full power it overheats in seconds (it can smoke).
// The dashboard slider sets 0-100 %, which is scaled to at most FLASH_MAX_DUTY of full power, and it switches
// itself off after FLASH_AUTO_OFF_S.
#define FLASH_MAX_DUTY    60       // 0-255 hardware limit (60 = about a quarter of full power). Don't go above 90.
#define FLASH_AUTO_OFF_S  60
#define FLASH_CHANNEL     7        // LEDC channel 7 (timer 3): the camera clock uses channel 0 / timer 0

// AI-Thinker camera pins
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

HardwareSerial Uno(2);
SemaphoreHandle_t dataLock, txLock;

// ---------------- data from the Uno ----------------
static char unoJson[1600] = "";
static uint32_t unoAt = 0;
static const char *SKELETON =
    "{\"mode\":\"manual\",\"state\":\"waiting for Arduino\",\"uptime\":0,\"object\":null,\"ambient\":null,"
    "\"airTemp\":null,\"humidity\":null,\"distance\":400,\"gas\":0,\"battery\":0,\"batteryPct\":0,\"score\":0,"
    "\"scanProgress\":100,\"pan\":90,\"motion\":false,\"pirReady\":false,\"gasAlarm\":false,\"batteryLow\":false,"
    "\"thermalOk\":true,\"dhtOk\":true,\"alert\":false,\"survivors\":0,\"scans\":0,"
    "\"finding\":{\"found\":false,\"fire\":false,\"background\":null,\"peak\":null,\"delta\":0,\"bearing\":0,\"cells\":0},"
    "\"grid\":{\"panMin\":20,\"panStep\":10,\"rows\":[[null,null,null,null,null,null,null,null,null,null,null,null,null,null,null],"
    "[null,null,null,null,null,null,null,null,null,null,null,null,null,null,null]]}}";

struct Event { uint32_t t; char kind[10]; int score; char text[84]; };
static const int LOG_SIZE = 24;
static Event events[LOG_SIZE];
static int logCount = 0;

static uint8_t flashLevel = 0;          // 0-100 % as shown on the dashboard
static uint32_t flashAt = 0;
static int8_t pendingLight = -1;        // car LED command resent until the Uno reports it
static uint8_t lightTries = 0;
static uint32_t lightSentAt = 0;

// Held controls: what the phone wants right now. loop() repeats it to the Uno and ends it when the phone goes quiet.
#define HOLD_RESEND_MS   100
#define HOLD_TIMEOUT_MS  600
static volatile int driveL = 0, driveR = 0;
static volatile uint32_t driveAt = 0, driveSentAt = 0;
static volatile bool driveActive = false, driveNew = false;
static volatile bool drillOn = false, drillNew = false;
static volatile uint32_t drillAt = 0, drillSentAt = 0;

static char pendingMode[8] = "";        // resent until the Uno reports it (survives lost bytes)
static uint8_t modeTries = 0;
static uint32_t modeSentAt = 0;

void sendUno(const char *line) {                      // "D,180,180" goes out as "D,180,180*5F" (XOR checksum)
  uint8_t x = 0;
  for (const char *p = line; *p; p++) x ^= (uint8_t)*p;
  char tail[6];
  snprintf(tail, sizeof tail, "*%02X", x);
  xSemaphoreTake(txLock, portMAX_DELAY);
  Uno.print(line);
  Uno.println(tail);
  xSemaphoreGive(txLock);
}

// A status line with a lost or broken byte would make the dashboard's JSON fail: such lines are dropped and the
// last good status is kept.
bool wholeJson(const char *j) {
  int depth = 0;
  bool str = false;
  char lastCh = 0;
  for (const char *p = j; *p; p++) {
    char c = *p;
    if ((uint8_t)c < 32) return false;
    if (str) {
      if (c == '\\') { if (!*++p) return false; }
      else if (c == '"') str = false;
      continue;
    }
    if (c == '"') str = true;
    else if (c == '{' || c == '[') depth++;
    else if ((c == '}' || c == ']') && --depth < 0) return false;
    if (c != ' ') lastCh = c;
  }
  return depth == 0 && !str && lastCh == '}';
}

void addEvent(const char *kind, int score, const char *text) {
  Event &e = events[logCount % LOG_SIZE];
  e.t = millis() / 1000;
  strlcpy(e.kind, kind, sizeof e.kind);
  e.score = score;
  strlcpy(e.text, text, sizeof e.text);
  logCount++;
}

void handleLine(char *line) {
  if (line[0] == 'S' && line[1] == '{') {
    if (!wholeJson(line + 1)) return;
    xSemaphoreTake(dataLock, portMAX_DELAY);
    strlcpy(unoJson, line + 1, sizeof unoJson);
    unoAt = millis();
    xSemaphoreGive(dataLock);
  } else if (line[0] == 'E' && line[1] == ',') {           // E,kind,score,text
    char *kind = line + 2, *p = strchr(kind, ',');
    if (!p) return;
    *p = 0;
    char *sc = p + 1, *q = strchr(sc, ',');
    if (!q) return;
    *q = 0;
    xSemaphoreTake(dataLock, portMAX_DELAY);
    addEvent(kind, atoi(sc), q + 1);
    xSemaphoreGive(dataLock);
  }
}

// ---------------- HTTP helpers ----------------
static void cors(httpd_req_t *req) { httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*"); }
static esp_err_t sendOk(httpd_req_t *req) {
  cors(req);
  httpd_resp_set_type(req, "application/json");
  return httpd_resp_sendstr(req, "{\"ok\":true}");
}
static bool queryArg(httpd_req_t *req, const char *key, char *out, size_t n) {
  char q[64];
  if (httpd_req_get_url_query_str(req, q, sizeof q) != ESP_OK) return false;
  return httpd_query_key_value(q, key, out, n) == ESP_OK;
}
static void jsonText(String &s, const char *t) {
  s += '"';
  for (; *t; t++) { if (*t == '"' || *t == '\\') s += '\\'; if ((uint8_t)*t >= 32) s += *t; }
  s += '"';
}

// ---------------- HTTP handlers ----------------
static esp_err_t indexHandler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, DASHBOARD_HTML, HTTPD_RESP_USE_STRLEN);
}

static esp_err_t infoHandler(httpd_req_t *req) {
  cors(req);
  httpd_resp_set_type(req, "application/json");
  return httpd_resp_sendstr(req, "{\"name\":\"" WIFI_SSID "\",\"firmware\":\"4.0-uno\",\"ws\":true,\"camera\":\"" CAM_URL "\"}");
}

static esp_err_t statusHandler(httpd_req_t *req) {
  String s;
  s.reserve(3200);
  xSemaphoreTake(dataLock, portMAX_DELAY);
  bool link = unoAt && millis() - unoAt < 2000;
  s = unoAt ? unoJson : SKELETON;
  s.remove(s.length() - 1);                                // drop the closing brace, then add our fields
  s += ",\"camera\":\"" CAM_URL "\",\"clients\":";
  s += WiFi.softAPgetStationNum();
  s += ",\"flash\":";
  s += flashLevel;
  s += ",\"link\":";
  s += link ? "true" : "false";
  s += ",\"events\":[";
  int n = min(logCount, 10);
  for (int i = 0; i < n; i++) {
    const Event &e = events[(logCount - 1 - i) % LOG_SIZE];
    s += i ? ",{" : "{";
    s += "\"t\":"; s += e.t; s += ",\"kind\":\""; s += e.kind; s += "\",\"text\":";
    jsonText(s, e.text);
    s += ",\"score\":"; s += e.score; s += '}';
  }
  s += "]}";
  xSemaphoreGive(dataLock);
  cors(req);
  httpd_resp_set_type(req, "application/json");
  return httpd_resp_send(req, s.c_str(), s.length());
}

void wantDrive(int l, int r) {          // from the WebSocket or /api/drive
  l = constrain(l, -255, 255); r = constrain(r, -255, 255);
  bool change = l != driveL || r != driveR || !driveActive;
  driveL = l; driveR = r; driveAt = millis();
  driveActive = l || r;
  if (change) driveNew = true;          // a new direction goes to the Uno at once (from loop, within ~2 ms)
}
void wantDrill(bool on) {
  if (on != drillOn) drillNew = true;
  drillOn = on; drillAt = millis();
}
// One control frame: "D,<l>,<r>" drive, "R,1" / "R,0" drill, "P" keep-alive.
void controlLine(const char *t) {
  int l, r;
  if (t[0] == 'D' && sscanf(t + 2, "%d,%d", &l, &r) == 2) wantDrive(l, r);
  else if (t[0] == 'R' && t[1] == ',') wantDrill(t[2] == '1');
}

static esp_err_t driveHandler(httpd_req_t *req) {
  char l[8] = "0", r[8] = "0";
  queryArg(req, "l", l, sizeof l);
  queryArg(req, "r", r, sizeof r);
  wantDrive(atoi(l), atoi(r));
  return sendOk(req);
}
static esp_err_t drillHandler(httpd_req_t *req) {   // /api/drill?on=1|0 (fallback when the WebSocket is down)
  char on[4] = "0";
  queryArg(req, "on", on, sizeof on);
  wantDrill(on[0] == '1');
  return sendOk(req);
}
static esp_err_t wsHandler(httpd_req_t *req) {
  if (req->method == HTTP_GET) return ESP_OK;         // handshake done
  httpd_ws_frame_t f = {};
  f.type = HTTPD_WS_TYPE_TEXT;
  esp_err_t e = httpd_ws_recv_frame(req, &f, 0);      // length first
  if (e != ESP_OK || f.len == 0 || f.len > 31) return e;
  uint8_t buf[32];
  f.payload = buf;
  e = httpd_ws_recv_frame(req, &f, f.len);
  if (e != ESP_OK) return e;
  buf[f.len] = 0;
  if (f.type == HTTPD_WS_TYPE_TEXT) controlLine((const char *)buf);
  return ESP_OK;
}

static esp_err_t modeHandler(httpd_req_t *req) {
  char m[8] = "manual", line[16];
  queryArg(req, "m", m, sizeof m);
  if (strcmp(m, "auto") && strcmp(m, "estop")) strcpy(m, "manual");
  snprintf(line, sizeof line, "M,%s", m);
  sendUno(line);
  if (!strcmp(m, "estop")) { sendUno(line); sendUno(line); }  // E-STOP: send three times at once
  if (strcmp(m, "manual")) { driveActive = false; driveL = driveR = 0; drillOn = false; }   // nothing held is repeated
  strlcpy(pendingMode, m, sizeof pendingMode);
  modeTries = 1;
  modeSentAt = millis();
  return sendOk(req);
}

static esp_err_t scanHandler(httpd_req_t *req) { sendUno("C"); sendUno("C"); return sendOk(req); }  // 2nd is ignored if the 1st arrived
static esp_err_t ackHandler(httpd_req_t *req) { sendUno("A"); sendUno("A"); return sendOk(req); }
static esp_err_t beepHandler(httpd_req_t *req) { sendUno("B"); return sendOk(req); }

static esp_err_t csvHandler(httpd_req_t *req) {
  String s = "seconds,kind,confidence,text\n";
  xSemaphoreTake(dataLock, portMAX_DELAY);
  int n = min(logCount, LOG_SIZE);
  for (int i = n - 1; i >= 0; i--) {
    const Event &e = events[(logCount - 1 - i) % LOG_SIZE];
    s += String(e.t) + "," + e.kind + "," + e.score + ",\"" + e.text + "\"\n";
  }
  xSemaphoreGive(dataLock);
  httpd_resp_set_type(req, "text/csv");
  httpd_resp_set_hdr(req, "Content-Disposition", "attachment; filename=resqbot_log.csv");
  return httpd_resp_send(req, s.c_str(), s.length());
}

static esp_err_t captureHandler(httpd_req_t *req) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) { httpd_resp_send_500(req); return ESP_FAIL; }
  cors(req);
  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=resqbot.jpg");
  esp_err_t r = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return r;
}

void setFlash(int level) {
  flashLevel = constrain(level, 0, 100);
  flashAt = millis();
  ledcWrite(FLASH_LED, (uint32_t)flashLevel * FLASH_MAX_DUTY / 100);
}

static esp_err_t ledHandler(httpd_req_t *req) {      // /led?level=0..100   (old form /led?on=1 = 30 %)
  char v[8] = "";
  if (queryArg(req, "level", v, sizeof v)) setFlash(atoi(v));
  else if (queryArg(req, "on", v, sizeof v)) setFlash(v[0] == '1' ? 30 : 0);
  return sendOk(req);
}

static esp_err_t headlightHandler(httpd_req_t *req) { // /api/headlight?on=1|0 -> car LED on the Uno (D13)
  char v[4] = "0";
  queryArg(req, "on", v, sizeof v);
  pendingLight = v[0] == '1';
  sendUno(pendingLight ? "L,1" : "L,0");
  lightTries = 1;
  lightSentAt = millis();
  return sendOk(req);
}

// Each video viewer gets its own small task, so one phone's stream never blocks another phone (before, the
// video server could only serve one phone and the next one waited forever).
static volatile uint32_t streamGen = 0;
static void streamTask(void *arg) {
  httpd_req_t *req = (httpd_req_t *)arg;
  uint32_t me = ++streamGen;
  httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=resqframe");
  cors(req);
  char head[96];
  while (streamGen - me < MAX_VIEWERS) {                    // a newer viewer over the limit replaces this one
    uint32_t t0 = millis();
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) { vTaskDelay(pdMS_TO_TICKS(30)); continue; }
    size_t n = snprintf(head, sizeof head, "\r\n--resqframe\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
                        (unsigned)fb->len);
    esp_err_t r = httpd_resp_send_chunk(req, head, n);
    if (r == ESP_OK) r = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    if (r != ESP_OK) break;                                 // viewer closed the page or left the Wi-Fi
    int32_t wait = FRAME_MS - (int32_t)(millis() - t0);
    if (wait > 0) vTaskDelay(pdMS_TO_TICKS(wait));
  }
  httpd_req_async_handler_complete(req);
  vTaskDelete(nullptr);
}

static esp_err_t streamHandler(httpd_req_t *req) {
  httpd_req_t *copy = nullptr;
  if (httpd_req_async_handler_begin(req, &copy) != ESP_OK) return ESP_FAIL;
  if (xTaskCreate(streamTask, "stream", 4096, copy, 5, nullptr) != pdPASS) {
    httpd_req_async_handler_complete(copy);
    return ESP_FAIL;
  }
  return ESP_OK;
}

void startServers() {
  // The chip has 16 network sockets in total. The old setup let both servers claim up to 18, so some phones
  // couldn't open the page at all. Now: dashboard + API 6, video 4 (+2 internal each) = 14.
  httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
  cfg.max_uri_handlers = 18;
  cfg.max_open_sockets = 6;
  cfg.lru_purge_enable = true;              // a phone that left without closing frees its socket for the next one
  cfg.recv_wait_timeout = 3;
  cfg.send_wait_timeout = 3;
  httpd_handle_t web = nullptr, stream = nullptr;
  const httpd_uri_t uris[] = {
      {"/", HTTP_GET, indexHandler, nullptr},          {"/api/info", HTTP_GET, infoHandler, nullptr},
      {"/api/status", HTTP_GET, statusHandler, nullptr}, {"/api/drive", HTTP_GET, driveHandler, nullptr},
      {"/api/mode", HTTP_GET, modeHandler, nullptr},     {"/api/scan", HTTP_GET, scanHandler, nullptr},
      {"/api/ack", HTTP_GET, ackHandler, nullptr},       {"/api/beep", HTTP_GET, beepHandler, nullptr},
      {"/api/log.csv", HTTP_GET, csvHandler, nullptr},   {"/capture", HTTP_GET, captureHandler, nullptr},
      {"/led", HTTP_GET, ledHandler, nullptr},           {"/api/headlight", HTTP_GET, headlightHandler, nullptr},
      {"/api/drill", HTTP_GET, drillHandler, nullptr},
  };
  if (httpd_start(&web, &cfg) == ESP_OK) {
    for (const auto &u : uris) httpd_register_uri_handler(web, &u);
    httpd_uri_t ws = {};
    ws.uri = "/ws"; ws.method = HTTP_GET; ws.handler = wsHandler; ws.is_websocket = true;
    httpd_register_uri_handler(web, &ws);
  }
  cfg.server_port = 81;                                     // video on its own server
  cfg.ctrl_port += 1;
  cfg.max_open_sockets = 4;
  cfg.lru_purge_enable = false;             // never cut a running video; old viewers end by MAX_VIEWERS instead
  httpd_uri_t streamUri = {"/stream", HTTP_GET, streamHandler, nullptr};
  if (httpd_start(&stream, &cfg) == ESP_OK) httpd_register_uri_handler(stream, &streamUri);
}

bool startCamera() {
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM; c.pin_d1 = Y3_GPIO_NUM; c.pin_d2 = Y4_GPIO_NUM; c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM; c.pin_d5 = Y7_GPIO_NUM; c.pin_d6 = Y8_GPIO_NUM; c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk = XCLK_GPIO_NUM; c.pin_pclk = PCLK_GPIO_NUM; c.pin_vsync = VSYNC_GPIO_NUM; c.pin_href = HREF_GPIO_NUM;
  c.pin_sccb_sda = SIOD_GPIO_NUM; c.pin_sccb_scl = SIOC_GPIO_NUM;
  c.pin_pwdn = PWDN_GPIO_NUM; c.pin_reset = RESET_GPIO_NUM;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = FRAMESIZE_VGA;          // 640x480, smooth over the robot's Wi-Fi
  c.jpeg_quality = 14;
  c.fb_count = psramFound() ? 2 : 1;
  c.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
  c.grab_mode = CAMERA_GRAB_LATEST;
  return esp_camera_init(&c) == ESP_OK;
}

void setup() {
  Serial.begin(115200);                                     // USB debug through the MB board
  pinMode(FLASH_LED, OUTPUT);
  digitalWrite(FLASH_LED, LOW);                             // flash off until the camera is ready
  dataLock = xSemaphoreCreateMutex();
  txLock = xSemaphoreCreateMutex();
  Uno.setRxBufferSize(2048);
  Uno.begin(115200, SERIAL_8N1, LINK_RX, LINK_TX);
  if (!startCamera()) {
    Serial.println("Camera init failed - check the ribbon cable");
    addEvent("hazard", 0, "Camera not working - check the ribbon cable");
  }
  ledcAttachChannel(FLASH_LED, 5000, 8, FLASH_CHANNEL);    // dimmable flash, after the camera took channel 0
  setFlash(0);
  WiFi.mode(WIFI_AP);
  WiFi.softAP(WIFI_SSID, WIFI_PASSWORD, WIFI_CHANNEL, 0, 4);  // up to 4 phones
  WiFi.setSleep(false);                                     // no Wi-Fi power saving: commands go out at once
  Serial.printf("Wi-Fi \"%s\" -> http://%s  (video :81/stream)\n", WIFI_SSID, WiFi.softAPIP().toString().c_str());
  startServers();
}

// Repeats the held drive / drill command to the Uno and ends it when the phone stops sending.
void holdControls() {
  uint32_t now = millis();
  if (driveNew || (driveActive && now - driveSentAt >= HOLD_RESEND_MS)) {
    driveNew = false;                                   // cleared first: a change arriving meanwhile is sent next pass
    bool stop = !driveActive;
    char cmd[24];
    snprintf(cmd, sizeof cmd, "D,%d,%d", stop ? 0 : (int)driveL, stop ? 0 : (int)driveR);
    sendUno(cmd);
    if (stop) sendUno(cmd);                             // a stop goes out twice
    driveSentAt = now;
  }
  if (driveActive && now - driveAt > HOLD_TIMEOUT_MS) { driveActive = false; driveL = driveR = 0; driveNew = true; }
  if (drillNew || (drillOn && now - drillSentAt >= 200)) {
    drillNew = false;
    bool on = drillOn;
    sendUno(on ? "R,1" : "R,0");
    if (!on) sendUno("R,0");
    drillSentAt = now;
  }
  if (drillOn && now - drillAt > HOLD_TIMEOUT_MS) { drillOn = false; drillNew = true; }
}

void loop() {
  holdControls();
  static char line[1700];
  static size_t len = 0;
  while (Uno.available()) {
    char ch = Uno.read();
    if (ch == '\n' || ch == '\r') {
      if (len) { line[len] = 0; handleLine(line); len = 0; }
    } else if (len < sizeof line - 1) {
      line[len++] = ch;
    } else {
      len = 0;                                              // over-long or broken line
    }
  }
  // Mode changes are repeated until the Uno's status shows them (a byte can be lost while it reads the DHT11).
  if (pendingMode[0] && millis() - modeSentAt > 300) {
    char want[24];
    snprintf(want, sizeof want, "\"mode\":\"%s\"", pendingMode);
    xSemaphoreTake(dataLock, portMAX_DELAY);
    bool done = strstr(unoJson, want) != nullptr;
    xSemaphoreGive(dataLock);
    if (done || modeTries >= 8) {
      pendingMode[0] = 0;
    } else {
      char cmd[16];
      snprintf(cmd, sizeof cmd, "M,%s", pendingMode);
      sendUno(cmd);
      modeTries++;
      modeSentAt = millis();
    }
  }
  if (pendingLight >= 0 && millis() - lightSentAt > 300) {
    xSemaphoreTake(dataLock, portMAX_DELAY);
    bool done = strstr(unoJson, pendingLight ? "\"headlight\":true" : "\"headlight\":false") != nullptr;
    xSemaphoreGive(dataLock);
    if (done || lightTries >= 8) pendingLight = -1;
    else { sendUno(pendingLight ? "L,1" : "L,0"); lightTries++; lightSentAt = millis(); }
  }
  if (flashLevel && millis() - flashAt > FLASH_AUTO_OFF_S * 1000UL) setFlash(0);   // never left on by mistake
  delay(1);
}
