/*
  ResQBot Mini - ESP32-CAM live video (AI-Thinker ESP32-CAM, OV2640)
  -------------------------------------------------------------------
  Joins the robot's own Wi-Fi with a fixed address and streams MJPEG video:
    http://192.168.4.50:81/stream      live video (shown on the robot dashboard)
    http://192.168.4.50/capture        one JPEG photo (evidence for rescuers)
    http://192.168.4.50/led?on=1       white flash LED on/off (lights up dark rubble)

  Board: "AI Thinker ESP32-CAM", Arduino-ESP32 core 3.x. Flash it with the ESP32-CAM-MB USB board.
  Wi-Fi name/password must match firmware/ResQBot/config.h.
*/
#include "esp_camera.h"
#include "esp_http_server.h"
#include <WiFi.h>

#define WIFI_SSID     "ResQBot-01"
#define WIFI_PASSWORD "rescue123"
IPAddress camIP(192, 168, 4, 50), gateway(192, 168, 4, 1), subnet(255, 255, 255, 0);

// AI-Thinker pin map
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
#define FLASH_LED 4

static const char *BOUNDARY = "resqframe";

static esp_err_t streamHandler(httpd_req_t *req) {
  httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=resqframe");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  char head[96];
  while (true) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) return ESP_FAIL;
    size_t n = snprintf(head, sizeof head, "\r\n--%s\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
                        BOUNDARY, (unsigned)fb->len);
    esp_err_t r = httpd_resp_send_chunk(req, head, n);
    if (r == ESP_OK) r = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    if (r != ESP_OK) return r;            // viewer closed the page
  }
}

static esp_err_t captureHandler(httpd_req_t *req) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) { httpd_resp_send_500(req); return ESP_FAIL; }
  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=resqbot.jpg");
  esp_err_t r = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return r;
}

static esp_err_t ledHandler(httpd_req_t *req) {
  char q[16] = "", v[4] = "0";
  httpd_req_get_url_query_str(req, q, sizeof q);
  httpd_query_key_value(q, "on", v, sizeof v);
  digitalWrite(FLASH_LED, v[0] == '1');
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_sendstr(req, "ok");
}

static void startServers() {
  httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
  httpd_handle_t web = nullptr, stream = nullptr;
  httpd_uri_t capture = {"/capture", HTTP_GET, captureHandler, nullptr};
  httpd_uri_t led = {"/led", HTTP_GET, ledHandler, nullptr};
  if (httpd_start(&web, &cfg) == ESP_OK) {
    httpd_register_uri_handler(web, &capture);
    httpd_register_uri_handler(web, &led);
  }
  cfg.server_port = 81;                   // stream on its own server so photos still work while streaming
  cfg.ctrl_port += 1;
  httpd_uri_t streamUri = {"/stream", HTTP_GET, streamHandler, nullptr};
  if (httpd_start(&stream, &cfg) == ESP_OK) httpd_register_uri_handler(stream, &streamUri);
}

void setup() {
  Serial.begin(115200);
  pinMode(FLASH_LED, OUTPUT);
  digitalWrite(FLASH_LED, LOW);

  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM; c.pin_d1 = Y3_GPIO_NUM; c.pin_d2 = Y4_GPIO_NUM; c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM; c.pin_d5 = Y7_GPIO_NUM; c.pin_d6 = Y8_GPIO_NUM; c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk = XCLK_GPIO_NUM; c.pin_pclk = PCLK_GPIO_NUM; c.pin_vsync = VSYNC_GPIO_NUM; c.pin_href = HREF_GPIO_NUM;
  c.pin_sccb_sda = SIOD_GPIO_NUM; c.pin_sccb_scl = SIOC_GPIO_NUM;
  c.pin_pwdn = PWDN_GPIO_NUM; c.pin_reset = RESET_GPIO_NUM;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = FRAMESIZE_VGA;           // 640x480: smooth over the robot's Wi-Fi
  c.jpeg_quality = 14;                    // 10 = best, 63 = smallest
  c.fb_count = psramFound() ? 2 : 1;
  c.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
  c.grab_mode = CAMERA_GRAB_LATEST;
  if (esp_camera_init(&c) != ESP_OK) {
    Serial.println("Camera init failed - check the ribbon cable");
    delay(3000);
    ESP.restart();
  }

  WiFi.mode(WIFI_STA);
  WiFi.config(camIP, gateway, subnet);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Joining robot Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) { delay(400); Serial.print('.'); }
  Serial.printf("\nCamera ready: http://%s:81/stream\n", WiFi.localIP().toString().c_str());
  startServers();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {    // robot restarted: rejoin
    WiFi.reconnect();
    delay(2000);
  }
  delay(100);
}
