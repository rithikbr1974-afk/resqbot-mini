"""One-off: rewrite docs/proposal/ResQBot_Proposal.html for the Arduino Uno + ESP32-CAM + DHT11 design."""
import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import make_bom  # noqa: E402

p = ROOT / "docs" / "proposal" / "ResQBot_Proposal.html"
s = p.read_text(encoding="utf-8")

# ---- parts table from the same data as the components PDF ----
rows, n, total, owned = [], 0, 0, 0
for group, parts in make_bom.PARTS:
    for name, why, qty, price, store, url, stock, alt in parts:
        n += 1
        line = qty * price
        total += line
        if name in make_bom.OWNED:
            owned += line
        rows.append(f'  <tr><td>{n}</td><td>{escape(name)}</td><td>{qty}</td><td>{escape(why)}</td><td class="r">{line:,}</td></tr>')
tbl = ('<table>\n  <tr><th>#</th><th>Component</th><th>Qty</th><th>Role in the robot</th><th class="r">₹</th></tr>\n' + "\n".join(rows) +
       f'\n  <tr class="total"><td></td><td colspan="3">Total — all {n} items bought new (online prices)</td><td class="r">₹{total:,}</td></tr>\n</table>')
a = s.index('<table>\n  <tr><th>#</th><th>Component</th>')
b = s.index('</table>', a) + len('</table>')
s = s[:a] + tbl + s[b:]
new = total - owned
print("total", total, "owned", owned, "new", new)


def rep(old, new_):
    global s
    assert old in s, "NOT FOUND: " + old[:70]
    s = s.replace(old, new_, 1)


rep('<div><b>₹2,965</b><span>full build, common parts</span></div>', f'<div><b>₹{new:,}</b><span>new parts (₹{total:,} all new)</span></div>')
rep('<span>thermal sweep from one ₹450 sensor</span>', '<span>thermal sweep from one ₹759 sensor</span>')
rep('built entirely from common hobby parts for <b>₹2,965</b>.',
    f'built entirely from common hobby parts: about <b>₹{new:,}</b> of new parts if you already own an Arduino Uno and an ESP32-CAM (₹{total:,} if everything is bought new).')
rep('turning a ₹450 sensor\ninto a 30-pixel thermal scanner. The ESP32 controller looks for', 'turning a ₹759 sensor\ninto a 30-pixel thermal scanner. The Arduino Uno looks for')
rep('person, and a PIR sensor checks for movement.', 'person, and a PIR sensor checks for movement. A DHT11 adds the air temperature and humidity at the scene.')
rep('<b>Stay under ₹3,000</b> with parts available in any electronics market or online store in India.',
    '<b>Keep the cost low</b>: about ₹3,600 of new parts, all available in any electronics market or online store in India.')
rep('Thermal + motion + gas + video, autonomous, offline', 'Thermal + motion + gas + air + video, autonomous, offline')
rep('<b class="t">1 · Thermal imaging on a ₹450 budget</b>', '<b class="t">1 · Thermal imaging for the price of one sensor</b>')
rep('<li><b>Sensing:</b> MLX90614 IR thermometer (I²C) on pan-tilt, HC-SR04 ultrasonic, HC-SR501 PIR, MQ-2 gas, battery monitor, ESP32-CAM.</li>',
    '<li><b>Sensing:</b> MLX90614 IR thermometer (I²C) on pan-tilt, DHT11 air temperature and humidity, HC-SR04 ultrasonic, HC-SR501 PIR, MQ-2 gas, battery monitor, ESP32-CAM.</li>')
rep('<li><b>Control:</b> ESP32 DevKit (dual-core 240 MHz, Wi-Fi).</li>',
    '<li><b>Control:</b> Arduino Uno reads every sensor and runs the search. The ESP32-CAM is the camera and the Wi-Fi/dashboard gateway, linked to the Uno by a serial cable.</li>')
rep('Figure 2 — Sensors feed the ESP32, which drives the motors, servos and alert outputs and serves the dashboard\nover its own Wi-Fi. The ESP32-CAM joins the same network at a fixed address and streams video straight to the phone.',
    'Figure 2 — Sensors feed the Arduino Uno, which drives the motors, servos and alert outputs. It sends all data to the ESP32-CAM over a serial link; the ESP32-CAM makes the Wi-Fi hotspot, serves the dashboard and streams live video at the same time.')
rep('<li><b>Interface:</b> web server with a JSON API and a single-file dashboard stored inside the firmware.</li>',
    '<li><b>Interface:</b> the ESP32-CAM runs a web server with a JSON API and a single-file dashboard stored inside its firmware, and forwards phone commands to the Uno.</li>')

a = s.index('<div class="grid2">\n  <div class="box"><h4>Lite version')
b = s.index('</div>\n</div>', a) + len('</div>\n</div>')
s = s[:a] + f'''<div class="grid2">
  <div class="box"><h4>What you may already own</h4>
  The Arduino Uno (₹249) and the ESP32-CAM (₹846) are common in student labs. Without them the rest of the robot costs about <b>₹{new:,}</b>.
  Small parts (resistors, capacitors, switch, jumpers) are cheaper at a local electronics shop.</div>
  <div class="box"><h4>Why these parts</h4>
  The MLX90614 is the cheapest reliable non-contact thermometer with a digital output. Thermal-array sensors (8 × 8 and up) cost
  several times more; sweeping one sensor gives a usable heat map within budget. Prices were read from Robu.in and Amazon.in on 9 October 2026.</div>
</div>''' + s[b:]
rep('<p class="small muted">Not included: a charger for the 18650 cells', '<p class="small muted">Not included: a 2S charger (about ₹549 once) for the battery pack')

rep('alt="Wiring diagram from ESP32 pins to each module"', 'alt="Wiring diagram from Arduino Uno pins to each module"')
rep('The pin numbers match <span class="mono">firmware/ResQBot/config.h</span>.', 'The pin numbers match <span class="mono">firmware/ResQBot_Uno/config.h</span>.')
a = s.index('<li><b>Analog sensors use ADC1 pins')
b = s.index('<li><b>Full schematics</b>')
s = s[:a] + '''<li><b>Everything on the Uno runs at 5 V.</b> The HC-SR04, PIR, MQ-2, DHT11 and MLX90614 module connect directly, with no level shifting.</li>
  <li><b>One level shifter only:</b> the Uno's 5 V serial output (D1) reaches the ESP32-CAM's 3.3 V input (IO13) through a 1 kΩ / 2 kΩ divider.</li>
  <li><b>Serial link:</b> D1 → IO13 and IO14 → D0 at 115200 baud. The D0 wire is unplugged while uploading to the Uno.</li>
  ''' + s[b:]
rep('Servos and the ESP32-CAM draw current spikes; the LM2596 (3 A) feeds them so the ESP32 never browns out.',
    'Servos and the ESP32-CAM draw current spikes; the LM2596 (3 A) feeds them, with a 470 µF capacitor on the rail and 220 µF at the camera, so neither board resets.')
rep("<li><b>The MLX90614 runs at 3.3 V</b>, so its I²C pull-ups match the ESP32's logic level.</li>",
    '<li><b>The MLX90614 and DHT11 modules</b> have their own regulators and pull-ups, so they sit directly on the 5 V rail.</li>')
rep('<li><b>ESP32-CAM</b> takes only 5 V and GND from the robot; it talks to the phone over Wi-Fi, so no extra signal wires are needed.</li>',
    '<li><b>ESP32-CAM</b> takes 5 V and GND plus the two serial wires; it talks to the phone over its own Wi-Fi. Leave its micro-SD slot empty (IO13/IO14 are SD pins).</li>')

rep('<p>The firmware is written for the Arduino-ESP32 core (version 3.x) and needs one library from the Library Manager\n(<i>ESP32Servo</i>); the thermal sensor is read directly over I²C. It is non-blocking: the web server, sensors and\nbehaviour all run in one fast loop, so the phone stays responsive even during a thermal sweep.</p>',
    '<p>Two programs: the <b>Arduino Uno</b> sketch (Servo and Wire built in, plus the Adafruit <i>DHT sensor library</i>) and the <b>ESP32-CAM</b> sketch (Arduino-ESP32 core 3.x). The Uno code is non-blocking: sensors, thermal sweep, search logic and the serial link all run in one fast loop. On the ESP32-CAM the video stream has its own server task, so live video and sensor data run at the same time.</p>')
a = s.index('<tr><th>File</th><th>What it does</th></tr>')
b = s.index('</table>', a)
s = s[:a] + '''<tr><th>File</th><th>What it does</th></tr>
  <tr><td><span class="mono">ResQBot_Uno/ResQBot_Uno.ino</span></td><td>Arduino Uno main code: sensors, thermal sweep, search state machine, motors, servos, alerts, serial link</td></tr>
  <tr><td><span class="mono">ResQBot_Uno/config.h</span></td><td>Every pin, speed and threshold in one place</td></tr>
  <tr><td><span class="mono">ResQBot_Uno/detection.h</span></td><td>Heat-blob finder and confidence score (pure C++)</td></tr>
  <tr><td><span class="mono">ResQCam_Gateway/ResQCam_Gateway.ino</span></td><td>ESP32-CAM: Wi-Fi hotspot, web server and API, MJPEG stream, photo, flash LED, serial bridge to the Uno</td></tr>
  <tr><td><span class="mono">ResQCam_Gateway/dashboard_html.h</span></td><td>The phone dashboard, embedded into the firmware</td></tr>
  <tr><td><span class="mono">dashboard/index.html</span></td><td>Dashboard source (open it in a browser for demo mode)</td></tr>
  <tr><td><span class="mono">sim/</span></td><td>Python copy of the detection logic, 12 scenario tests, range model</td></tr>
''' + s[b:]
rep('<td>All telemetry as JSON: mode, state, temperatures, distance, gas, battery, heat map, finding, events</td>',
    '<td>All telemetry as JSON: mode, state, IR and air temperature, humidity, distance, gas, battery, heat map, finding, events, link status</td>')
rep('<span class="mono">192.168.4.50:81/stream</span>, <span class="mono">/capture</span>, <span class="mono">/led?on=1</span></td><td>ESP32-CAM video, photo, flash</td>',
    '<span class="mono">192.168.4.1:81/stream</span>, <span class="mono">/capture</span>, <span class="mono">/led?on=1</span></td><td>Live video, photo, flash light</td>')
rep('<li>Both sketches compile for their boards with Arduino-ESP32 core 3.3 (main: 76 % of flash, camera: 32 %).</li>',
    '<li>Both sketches compile for their boards: Arduino Uno (64 % of flash, 51 % of RAM) and ESP32-CAM with Arduino-ESP32 core 3.3 (33 % of flash).</li>')
rep('as implemented in <span class="mono">firmware/ResQBot/robot.h</span>.', 'as implemented in <span class="mono">firmware/ResQBot_Uno/ResQBot_Uno.ino</span>.')

rep('with the Arduino IDE 2.x, and a micro-USB cable.</p>', 'with the Arduino IDE 2.x, a USB-B cable for the Uno and a micro-USB cable for the ESP32-CAM programmer board.</p>')
rep('Remove the ENA and ENB jumpers (the ESP32 controls speed).', 'Remove the ENA and ENB jumpers (the Uno controls speed).')
rep('<li><b>Controller.</b> Fix the ESP32 on the upper plate on a perfboard with female headers. Wire it exactly as in Figure 3.\n    Join every GND.</li>',
    '<li><b>Controller.</b> Fix the Arduino Uno on the upper plate. Wire it exactly as in Figure 3 and the schematics. Join every GND.</li>')
rep('(upload the firmware once, it centres them)', '(upload the Uno firmware once, it centres them)')
rep('HC-SR04 at the front bumper (1k/2k divider on ECHO); PIR on top facing forward; MQ-2 on top with a\n    10k/20k divider on AO; battery divider 100k/47k to GPIO 35.',
    'HC-SR04 at the front bumper (TRIG A2, ECHO A3); PIR on D4 facing forward; MQ-2 on A0; DHT11 on D2 where air can reach it; battery divider 10k/10k to A1.')
rep('on GPIO 23; LED beacon on GPIO 2 through', 'on D3; LED beacon on D13 through')
rep('<li><b>Camera.</b> Mount the ESP32-CAM at the front facing forward; power it from the 5 V rail.</li>',
    '<li><b>Camera.</b> Mount the ESP32-CAM at the front facing forward; 5 V and GND from the rail, Uno D1 → 1 kΩ → IO13 (2 kΩ to GND), IO14 → Uno D0.</li>')
a = s.index('<li>Arduino IDE → Boards Manager')
b = s.index('</ol>', a)
s = s[:a] + '''<li>Arduino IDE → Boards Manager → install <b>esp32 by Espressif</b> (3.x). Library Manager → install <b>DHT sensor library</b> (Adafruit) with <b>Adafruit Unified Sensor</b>.</li>
  <li><b>Uno:</b> unplug the D0 wire, open <span class="mono">firmware/ResQBot_Uno/ResQBot_Uno.ino</span> (config.h and detection.h open with it), choose <b>Arduino Uno</b>, upload once, then plug D0 back in.</li>
  <li><b>ESP32-CAM:</b> put it on its MB USB board, open <span class="mono">firmware/ResQCam_Gateway/ResQCam_Gateway.ino</span>, choose <b>AI Thinker ESP32-CAM</b>, upload.</li>
  <li>To change the Wi-Fi name or password, edit the top of the ESP32-CAM sketch.</li>
  <li>After editing the dashboard, run <span class="mono">python tools/embed_dashboard.py</span> and upload the ESP32-CAM again.</li>
  ''' + s[b:]
rep('<tr><td>"Thermal sensor NOT found"</td><td>Check SDA→21, SCL→22, VIN→3V3; GY-906 address must be 0x5A</td></tr>',
    '<tr><td>"Thermal sensor not responding"</td><td>SDA → A4, SCL → A5, VIN → 5 V; GY-906 address must be 0x5A</td></tr>\n'
    "  <tr><td>\"Arduino not responding\"</td><td>Check D1 → 1k → IO13, IO14 → D0 and the common GND; unplug the Uno's USB cable</td></tr>\n"
    '  <tr><td>"DHT11 not responding"</td><td>DATA on D2; a bare 4-pin sensor needs a 10 kΩ pull-up to 5 V</td></tr>')
rep("<tr><td>ESP32 resets when the servos move</td><td>Servos must be on the LM2596 5 V rail, not the ESP32's 3V3 pin</td></tr>",
    '<tr><td>A board resets when the servos move</td><td>Servos must be on the LM2596 5 V rail; check the 470 µF capacitor</td></tr>')
rep('<tr><td>Camera shows "offline"</td><td>Power the robot first, then the camera; same Wi-Fi name and password in both sketches</td></tr>',
    '<tr><td>Camera shows "offline"</td><td>Reseat the camera ribbon; add 220–470 µF at the 5 V pins of the camera; keep its power wires short</td></tr>')
rep('can be delivered for under ₹3,000 with parts\nanyone can buy.', 'can be delivered for about ₹3,600 of new parts (an Arduino Uno, an ESP32-CAM and common modules\nanyone can buy).')

a = s.index('<h3>A.1 Pin map (ESP32 DevKit V1)</h3>')
b = s.index('</table>', a) + len('</table>')
s = s[:a] + '''<h3>A.1 Pin map (Arduino Uno)</h3>
<table>
  <tr><th>Pin</th><th>Connected to</th><th>Pin</th><th>Connected to</th></tr>
  <tr><td>A0</td><td>MQ-2 AO</td><td>D5 / D6</td><td>L298N ENA / ENB (speed, PWM)</td></tr>
  <tr><td>A1</td><td>Battery divider (10k/10k)</td><td>D7 / D8</td><td>L298N IN1 / IN2</td></tr>
  <tr><td>A2 / A3</td><td>HC-SR04 TRIG / ECHO</td><td>D9 / D10</td><td>L298N IN3 / IN4</td></tr>
  <tr><td>A4 / A5</td><td>MLX90614 SDA / SCL</td><td>D11 / D12</td><td>Servo pan / tilt signal</td></tr>
  <tr><td>D0 / D1</td><td>ESP32-CAM IO14 / IO13 (D1 via 1k/2k)</td><td>D3</td><td>Buzzer (via BC547)</td></tr>
  <tr><td>D2</td><td>DHT11 data</td><td>D13</td><td>LED beacon (via BC547)</td></tr>
  <tr><td>D4</td><td>PIR output</td><td>5V / GND</td><td>+5V rail / common ground</td></tr>
</table>''' + s[b:]
rep('firmware/ResQBot/   main robot firmware (ESP32 DevKit)\n  firmware/ResQCam/   camera firmware (ESP32-CAM)',
    'firmware/ResQBot_Uno/        main robot firmware (Arduino Uno)\n  firmware/ResQCam_Gateway/   camera, Wi-Fi and dashboard firmware (ESP32-CAM)')
rep('<li>Espressif Systems, <i>ESP32 Series Datasheet</i> and <i>Arduino-ESP32 documentation</i> (ADC, LEDC, Wi-Fi soft-AP).</li>',
    '<li>Arduino, <i>Arduino Uno R3 documentation</i>; Espressif Systems, <i>Arduino-ESP32 documentation</i> (Wi-Fi soft-AP).</li>')
rep('<li>HC-SR04 ultrasonic ranging module and HC-SR501 PIR module datasheets.</li>\n  <li>ESP32Servo library (Arduino Library Manager).</li>',
    '<li>HC-SR04 ultrasonic ranging module, HC-SR501 PIR module and Aosong DHT11 datasheets.</li>\n  <li>Adafruit DHT sensor library and the Arduino Servo library.</li>')

p.write_text(s, encoding="utf-8")
left = re.findall(r'[^<>]{0,50}(?:ESP32 DevKit|GPIO|ESP32Servo|ADC1|192\.168\.4\.50)[^<>]{0,40}', s)
print("leftovers:", left)
