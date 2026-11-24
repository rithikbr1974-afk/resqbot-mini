# ResQBot Mini

A low-cost thermal search-and-rescue rover. **Arduino Uno** is the main board: it reads every sensor (MLX90614 thermal
on a pan-tilt, DHT11, HC-SR04, HC-SR501 PIR, MQ-2, battery), finds and confirms body heat (heat contrast + size +
warmer-when-closer + motion → 0–100 confidence), and drives the motors, servos, buzzer and beacon. The **ESP32-CAM**
streams live video, runs the Wi-Fi hotspot and the phone dashboard, and gets all sensor data from the Uno over a serial link.

**Build it:** `docs/ResQBot_Setup_Guide.pdf` (wiring, upload, first test) · `docs/ResQBot_Schematics.pdf` (7 sheets + netlist)
· `docs/ResQBot_Components.pdf` (parts with buy links and prices).

| Folder | Contents |
|---|---|
| `firmware/ResQBot_Uno/` | Arduino Uno main firmware (libraries: Servo, Wire, DHT sensor library + Adafruit Unified Sensor) |
| `firmware/ResQCam_Gateway/` | ESP32-CAM firmware: camera stream, Wi-Fi AP, dashboard, serial bridge (board: AI Thinker ESP32-CAM) |
| `firmware/legacy_esp32_devkit/` | Earlier single-ESP32 version, kept for reference only |
| `dashboard/` | Phone dashboard (embedded into the ESP32-CAM). Open `index.html` in a browser for demo mode |
| `sim/` | Python copy of the detection logic: `python sim/test_detection.py` (12 tests), range model `python sim/fov_model.py` |
| `docs/` | Setup guide, schematics, components list, proposal, diagrams, phone-app prompt (`docs/app/`) |
| `website/` | Project website (`python tools/build_site.py`) |
| `tools/` | `embed_dashboard.py`, `make_bom.py`, `build_site.py`, `render_diagrams.ps1`, `build_pdf.ps1` |

## Quick start

1. Wire it as in the setup guide (power first, LM2596 set to 5.0 V before connecting anything).
2. Upload `firmware/ResQBot_Uno` to the Uno **with the D0 wire unplugged**.
3. Upload `firmware/ResQCam_Gateway` to the ESP32-CAM on its MB board.
4. Power on (two beeps), join Wi-Fi `ResQBot-01` (password `rescue123`), open http://192.168.4.1.

## Uno ⇄ ESP32-CAM link

Uno D1 → 1k/2k divider → ESP32-CAM IO13 · ESP32-CAM IO14 → Uno D0 · 115200 baud · common GND.
Uno sends `S{json status}` every 0.4 s and `E,kind,score,text` events; the ESP32-CAM sends `D,l,r`, `M,auto|manual|estop`, `C`, `A`, `B`.
