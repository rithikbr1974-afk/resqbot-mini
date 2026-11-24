"""ResQBot Mini setup walkthrough video: slides (HTML -> PNG via Edge) + Kokoro narration -> MP4 with ffmpeg.

Run with Karen's venv (has kokoro_onnx):  python video/make_walkthrough.py [--only-slides]
Output: video/ResQBot_Setup_Walkthrough.mp4
"""
import html
import json
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "video"
BUILD = OUT / "build"
IMG = ROOT / "docs" / "images"
SCH = OUT / "assets"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
KOKORO = Path(os.environ.get("KOKORO_DIR", "models"))
VOICE, SPEED = "af_heart", 1.0

CHAPTERS = ["Intro", "Parts", "Software", "Wiring", "Upload", "First test", "Dashboard", "Calibrate", "Fixes"]

# ---------------- spoken-text fixes (captions keep the written form) ----------------
SAY = [("ResQBot-01", "Rescue Bot dash zero one"), ("ResQBot", "Rescue Bot"), ("ESP32-CAM-MB", "E S P 32 cam M B"),
       ("ESP32-CAM", "E S P 32 cam"), ("ESP32", "E S P 32"), ("MLX90614", "M L X nine zero six one four"),
       ("DHT11", "D H T eleven"), ("HC-SR04", "H C S R zero four"), ("HC-SR501", "H C S R five zero one"),
       ("MQ-2", "M Q two"), ("LM2596", "L M twenty-five ninety-six"), ("L298N", "L two nine eight N"),
       ("BC547", "B C five four seven"), ("SG90", "S G ninety"), ("192.168.4.1", "one nine two dot one six eight dot four dot one"),
       ("config.h", "config dot H"), (".ino", " dot I N O"), ("IO13", "I O thirteen"), ("IO14", "I O fourteen"),
       ("IO0", "I O zero"), ("RST", "R S T"), ("VBAT", "V bat"), ("°C", " degrees"), ("µF", " microfarad"),
       ("nF", " nanofarad"), ("kΩ", " kilo-ohm"), ("Ω", " ohm"), ("CSV", "C S V"), ("E-STOP", "E stop"),
       ("rescue123", "rescue one two three"), ("D0", "D zero"), ("USB-B", "USB B"), ("TURN_DEG_PER_SEC", "turn degrees per second"),
       ("GAS_ALARM_RAW", "gas alarm raw"), ("BATTERY_ADC_CAL", "battery A D C cal"), ("DELTA_MIN_C", "delta min C"),
       ("TILT_ANGLES", "tilt angles"), ("Wi-Fi", "Wi-Fi"), ("5.0 V", "five point zero volts"), ("3.3 V", "three point three volts"),
       ("5 V", "five volts"), ("7.4 V", "seven point four volts"), ("3 A", "three amp"), ("IDE", "I D E"), ("PIR", "P I R"),
       ("SDA", "S D A"), ("SCL", "S C L"), ("ENA", "E N A"), ("ENB", "E N B"), ("IN1", "in one"), ("IN4", "in four"),
       ("OUT1", "out one"), ("OUT2", "out two"), ("OUT3", "out three"), ("OUT4", "out four"), ("GND", "ground"), ("cm", " centimeters")]


def spoken(text):
    for a, b in SAY:
        text = text.replace(a, b)
    return text


# ---------------- slide pieces ----------------
_sizes = {}


def crop(path, x, y, w, h, box=(1010, 740)):
    """An image region scaled to fit the visual box."""
    path = Path(path)
    if path not in _sizes:
        _sizes[path] = Image.open(path).size
    sw, sh = _sizes[path]
    sc = min(box[0] / w, box[1] / h)
    bw, bh = w * sc, h * sc                      # frame fits the crop exactly
    left, top = -x * sc, -y * sc
    return (f'<div class="crop" style="width:{bw:.0f}px;height:{bh:.0f}px"><img src="{path.as_uri()}" '
            f'style="width:{sw * sc:.0f}px;left:{left:.0f}px;top:{top:.0f}px"></div>')


def full(path, box=(1010, 740)):
    w, h = Image.open(path).size
    return crop(path, 0, 0, w, h, box)


def ide(title, path, body):
    crumbs = " <span>▸</span> ".join(html.escape(p) for p in path)
    return f'''<div class="win"><div class="bar"><i></i><i></i><i></i><b>{html.escape(title)}</b></div>
<div class="crumbs">{crumbs}</div><div class="wbody">{body}</div></div>'''


def code(lines, hl=()):
    rows = "".join(f'<div class="ln{" hl" if i in hl else ""}"><span>{i + 1}</span>{html.escape(l) or "&nbsp;"}</div>'
                   for i, l in enumerate(lines))
    return f'<div class="code">{rows}</div>'


def card(icon, big, small, tone="accent"):
    return f'<div class="callout {tone}"><div class="ic">{icon}</div><div><b>{html.escape(big)}</b><p>{html.escape(small)}</p></div></div>'


def table(rows):
    head = "".join(f"<th>{html.escape(c)}</th>" for c in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
    return f'<table class="tbl"><tr>{head}</tr>{body}</table>'


def bullets(items, hl=None):
    return "<ul>" + "".join(f'<li class="{"hl" if i == hl else ""}">{html.escape(t)}</li>' for i, t in enumerate(items)) + "</ul>"


# ---------------- assets ----------------
W2 = IMG / "wiring.png"           # 3200 x 2680 (2x of 1600 x 1340)
DASH = IMG / "dashboard_desktop.png"   # 2200 x 2800
PHONE = IMG / "dashboard_phone.png"
FLOW = IMG / "flowchart.png"


def wire(x, y, w, h):              # wiring.png in 1x coordinates
    return crop(W2, x * 2, y * 2, w * 2, h * 2)


def sch(n, x, y, w, h):            # schematic sheets in 1x coordinates (rendered 2x)
    return crop(SCH / f"sheet{n}.png", x * 2, y * 2, w * 2, h * 2)


# ---------------- the script ----------------
B = []   # beats: dict(ch, title, left, right, say, cap)


def beat(ch, title, say, left="", right="", cap=None, layout="split"):
    B.append(dict(ch=ch, title=title, say=say, cap=cap or say, left=left, right=right, layout=layout))


# 0 intro
beat(0, "Build and set up ResQBot Mini", "This walkthrough shows you how to build, program and use ResQBot Mini, the thermal search and rescue robot, from an empty table to a working robot.",
     left=bullets(["Low-cost thermal rescue rover", "Arduino Uno + ESP32-CAM", "Controlled from any phone"]), right=crop(DASH, 25, 126, 2147, 1224))
two = ["Arduino Uno: reads every sensor and drives the robot", "ESP32-CAM: live video, Wi-Fi hotspot and the dashboard", "Your phone: the control room"]
beat(0, "Two boards, one robot", "The robot has two boards. The Arduino Uno reads every sensor and drives the motors. The ESP32-CAM streams live video, makes the robot's own Wi-Fi, and shows everything on your phone.",
     left=bullets(two), right=sch(1, 30, 100, 1620, 900))
beat(0, "Two boards, one robot", "The two boards talk over a simple serial link. The Uno sends a full status update every 0.4 seconds, and the camera board passes your phone's commands back to the Uno.",
     left=bullets(two + ["Serial link at 115200 baud between them"], hl=3), right=sch(1, 700, 140, 950, 190))
beat(0, "Eight steps", "We will go in eight steps: parts and tools, software, wiring, uploading the code, the first test, using the dashboard, calibration, and fixing common problems.",
     left=bullets(["1  Parts and tools", "2  Software", "3  Wiring", "4  Upload the code", "5  First test", "6  Using the dashboard", "7  Calibration", "8  Troubleshooting"]),
     right=full(FLOW))

# 1 parts
beat(1, "What goes on the robot", "Here is everything that goes on the robot. You already have the Uno and the ESP32-CAM. The full list, with prices and buy links, is in the components PDF.",
     left=bullets(["Arduino Uno + ESP32-CAM (you have these)", "ESP32-CAM-MB programmer board", "MLX90614 thermal sensor + DHT11", "HC-SR04, HC-SR501 PIR, MQ-2", "L298N + 4WD chassis kit", "2 × SG90 servos + pan-tilt bracket", "7.4 V Li-ion pack + LM2596"]),
     right=table([["Part", "Role"], ["MLX90614", "body heat"], ["DHT11", "air temperature, humidity"], ["HC-SR04", "distance"], ["HC-SR501", "movement"],
                  ["MQ-2", "smoke and gas"], ["L298N", "motors"], ["LM2596", "5 V rail"], ["ESP32-CAM", "video, Wi-Fi, website"]]))
beat(1, "Small parts", "You also need a handful of small parts: eight resistors, two BC547 transistors, a diode, a few capacitors and a fuse. Any local electronics shop has them.",
     left=bullets(["Resistors: 1 kΩ ×3, 2 kΩ, 10 kΩ ×3, 100 Ω", "2 × BC547 transistors, 1 × 1N4148 diode", "470 µF, 220 µF, 4 × 100 nF capacitors", "3 A fuse and holder, rocker switch", "Jumper wires, zero PCB, berg strips"]),
     right=card("🧰", "About ₹55 at a local shop", "The resistor values match the schematic: R1–R8."))
beat(1, "Tools", "For tools you need a soldering iron, a multimeter, a small screwdriver, and two USB cables: the Uno's USB-B cable and a micro USB cable for the ESP32-CAM programmer board.",
     left=bullets(["Soldering iron and solder", "Multimeter (needed for the 5 V setting)", "Small screwdriver, glue gun", "USB-B cable for the Uno", "Micro-USB cable for the ESP32-CAM-MB"]),
     right=card("🔧", "A multimeter is a must", "You will use it to set the 5 V supply before anything is connected."))

# 2 software
beat(2, "Install the Arduino IDE", "Install the Arduino IDE, version 2, from arduino dot cc. It is free.",
     right=ide("arduino.cc/en/software", ["Software", "Arduino IDE 2"], '<div class="field big">Arduino IDE 2.x · Windows · Download</div><p class="note">Free · Windows, macOS, Linux</p>'),
     left=bullets(["arduino.cc → Software", "Arduino IDE 2.x", "Install with the default options"]), cap="Install the Arduino IDE, version 2, from arduino.cc. It is free.")
url = "https://espressif.github.io/arduino-esp32/package_esp32_index.json"
beat(2, "Add the ESP32 boards", "Open File, Preferences, and paste this address into Additional boards manager URLs. It tells the IDE where to find the ESP32 boards.",
     right=ide("Arduino IDE 2", ["File", "Preferences…"], f'<label>Additional boards manager URLs</label><div class="field hl">{url}</div><div class="btns"><span>Cancel</span><span class="go">OK</span></div>'),
     left=bullets(["File → Preferences", "Additional boards manager URLs", "Paste the address, click OK"]))
beat(2, "Install the ESP32 core", "Then open Tools, Board, Boards Manager, search for ESP32, and install esp32 by Espressif Systems, version 3 or newer. Arduino Uno support is already built in.",
     right=ide("Arduino IDE 2", ["Tools", "Board", "Boards Manager…"], '<div class="field">esp32</div><div class="item"><b>esp32</b> by Espressif Systems<span>3.x</span><span class="go">INSTALL</span></div><div class="item dim"><b>Arduino AVR Boards</b> · built in (Uno)<span>installed</span></div>'),
     left=bullets(["Tools → Board → Boards Manager", "Search: esp32", "esp32 by Espressif Systems → Install"]))
beat(2, "Install the DHT library", "Next, open Sketch, Include Library, Manage Libraries. Search for DHT sensor library by Adafruit and click Install. When it asks, choose Install all, so the Adafruit Unified Sensor library comes too.",
     right=ide("Arduino IDE 2", ["Sketch", "Include Library", "Manage Libraries…"], '<div class="field">DHT sensor library</div><div class="item"><b>DHT sensor library</b> by Adafruit<span class="go">INSTALL</span></div><div class="dialog">Install library dependencies? <b>Adafruit Unified Sensor</b><span class="go">INSTALL ALL</span></div>'),
     left=bullets(["Sketch → Include Library → Manage Libraries", "DHT sensor library (Adafruit) → Install", "Choose Install all", "Servo and Wire are built in"]))
beat(2, "Open the project", "Unzip the project. The code is in the firmware folder: ResQBot_Uno for the Arduino, and ResQCam_Gateway for the camera board. Keep each folder's files together, because the IDE needs the folder name to match the .ino file.",
     right=code(["ResQBot_Mini/", "  firmware/", "    ResQBot_Uno/          → Arduino Uno", "      ResQBot_Uno.ino", "      config.h", "      detection.h", "    ResQCam_Gateway/      → ESP32-CAM",
                 "      ResQCam_Gateway.ino", "      dashboard_html.h", "  docs/  (setup guide, schematics)"], hl=(2, 6)),
     left=bullets(["Unzip ResQBot_Mini_Project.zip", "Uno code: firmware/ResQBot_Uno", "Camera code: firmware/ResQCam_Gateway"]),
     cap="Unzip the project. The code is in the firmware folder: ResQBot_Uno for the Arduino and ResQCam_Gateway for the camera board. Keep each folder's files together.")

# 3 wiring
beat(3, "Power first", "Now the wiring. Always work with the battery unplugged, and build the power section first, before anything else is connected.",
     left=card("⚠️", "Battery unplugged while wiring", "Build and test the power section before connecting any board.", "warn"), right=sch(2, 30, 120, 1320, 440))
beat(3, "Battery, fuse, switch", "The battery pack goes through the DC jack, a 3 A fuse and the power switch. That point is called VBAT, the raw battery voltage.",
     left=bullets(["Battery → DC jack", "→ 3 A fuse → switch", "= VBAT (7.4 V)"]), right=sch(2, 40, 130, 720, 300))
beat(3, "Two loads on VBAT", "VBAT feeds two things: the L298N motor driver's 12 volt terminal, and the input of the LM2596 step-down converter.",
     left=bullets(["VBAT → L298N +12V terminal", "VBAT → LM2596 IN+", "Battery − → both GND / IN−"]), right=sch(2, 600, 120, 760, 440))
beat(3, "Set 5.0 V before anything else", "Before connecting anything else, switch on and turn the small screw on the LM2596 until its output reads exactly 5.0 V on your multimeter. This step protects every board on the robot.",
     left=card("🎯", "LM2596 OUT = 5.0 V", "Turn the brass screw slowly while measuring OUT+ to OUT−.", "warn"), right=sch(2, 760, 400, 600, 160))
beat(3, "The 5 V rail", "Solder the 470 µF and the 100 nF capacitors across the LM2596 output. This output is now the plus 5 volt rail that feeds the whole robot.",
     left=bullets(["C1 470 µF (+ to 5 V)", "C2 100 nF", "= the +5V rail"]), right=sch(2, 980, 400, 680, 320))
beat(3, "Power the Uno", "Connect the 5 volt rail to the Uno's 5V pin, not to VIN or the barrel jack, and join the Uno's GND to the common ground. Every ground on the robot must be joined together.",
     left=bullets(["+5V rail → Uno 5V pin", "VIN and barrel jack: not used", "All GNDs joined together"], hl=2), right=wire(250, 300, 750, 220))
beat(3, "Thermal sensor", "Now the sensors. The MLX90614 thermal sensor connects to 5 volts and ground, with SDA to A4 and SCL to A5.",
     left=bullets(["MLX90614 VIN → +5V", "GND → GND", "SDA → A4", "SCL → A5"]), right=wire(250, 680, 750, 120))
beat(3, "DHT11", "The DHT11 goes to 5 volts and ground, with its data pin on D2. If you use a bare four-pin DHT11, add a 10 kΩ resistor from data to 5 volts.",
     left=bullets(["VCC → +5V, GND → GND", "DATA → D2", "Bare sensor: 10 kΩ from DATA to +5V"]), right=sch(4, 580, 540, 520, 420))
beat(3, "Distance sensor", "The ultrasonic sensor's trigger goes to A2 and echo to A3. Because the Uno runs at 5 volts, no divider is needed.",
     left=bullets(["HC-SR04 VCC → +5V", "TRIG → A2", "ECHO → A3", "GND → GND"]), right=wire(250, 590, 750, 110))
beat(3, "Motion and gas", "The PIR motion sensor's output goes to D4, and the MQ-2 gas sensor's analog output goes to A0.",
     left=bullets(["PIR OUT → D4", "MQ-2 AO → A0", "Both: VCC → +5V, GND → GND"]), right=wire(250, 370, 1250, 190))
beat(3, "Battery reading", "For the battery reading, two 10 kΩ resistors divide VBAT in half into A1, with a 100 nF capacitor to ground.",
     left=bullets(["VBAT → 10 kΩ → A1", "A1 → 10 kΩ → GND", "100 nF from A1 to GND"]), right=sch(4, 1120, 540, 520, 420))
beat(3, "Motor driver", "On the L298N, remove the ENA and ENB jumpers. Connect ENA to D5, ENB to D6, and IN1 to IN4 to D7, D8, D9 and D10.",
     left=bullets(["Remove ENA and ENB jumpers", "ENA → D5, ENB → D6", "IN1 → D7, IN2 → D8", "IN3 → D9, IN4 → D10"]), right=wire(650, 420, 800, 270))
beat(3, "Motors", "Wire the two left motors in parallel to OUT1 and OUT2, and the two right motors to OUT3 and OUT4.",
     left=bullets(["Left pair → OUT1 / OUT2", "Right pair → OUT3 / OUT4", "100 nF across each pair"]), right=sch(5, 40, 110, 1060, 640))
beat(3, "Pan-tilt servos", "The pan servo's orange signal wire goes to D11 and the tilt servo's to D12. Red goes to 5 volts and brown to ground.",
     left=bullets(["Pan servo signal → D11", "Tilt servo signal → D12", "Red → +5V, brown → GND"]), right=sch(5, 1120, 110, 520, 640))
beat(3, "Buzzer and beacon", "The buzzer and the beacon LED are switched by BC547 transistors. D3 drives the buzzer and D13 drives the beacon, each through a 1 kΩ resistor.",
     left=bullets(["D3 → 1 kΩ → Q1 → buzzer", "D13 → 1 kΩ → Q2 → LED", "LED gets 100 Ω from +5V", "Diode across the buzzer"]), right=sch(6, 40, 110, 1060, 560))
beat(3, "Camera board power", "Finally, the link to the ESP32-CAM. Power it from 5 volts and ground, with a 220 µF capacitor close to the board.",
     left=bullets(["ESP32-CAM 5V → +5V", "GND → GND", "220 µF across 5V and GND"]), right=sch(6, 1120, 110, 520, 560))
beat(3, "The serial link", "Uno D1 goes through a 1 kΩ resistor to the camera's IO13, with a 2 kΩ resistor from IO13 to ground. This turns 5 volts into a safe 3.3 V. Camera IO14 goes straight to Uno D0.",
     left=bullets(["Uno D1 → 1 kΩ → IO13", "IO13 → 2 kΩ → GND", "IO14 → Uno D0", "TX always goes to RX"], hl=0), right=sch(6, 1130, 170, 500, 330))
beat(3, "Check before power", "Leave the camera's memory card slot empty, because those pins carry the link. Then check every connection against the setup guide's table before you power up.",
     left=card("✅", "Check every wire", "Use the connection table in the setup guide. Leave the micro-SD slot empty.", "ok"), right=wire(0, 130, 1600, 870))

# 4 upload
beat(4, "Settings live in config.h", "Before uploading, you can change settings. On the Uno, everything lives in config.h: pins, speeds and detection thresholds. The defaults match this wiring, so you do not need to change anything now.",
     right=code(["#define PIN_ENA   5    // left motors speed", "#define PIN_ENB   6    // right motors speed", "#define PIN_DHT   2    // DHT11 data", "#define DRIVE_SPEED   170",
                 "#define OBSTACLE_CM    25", "#define DELTA_MIN_C   1.5   // warm cell threshold", "#define ALERT_SCORE    60", "#define GAS_ALARM_RAW 400"], hl=(5, 6)),
     left=bullets(["ResQBot_Uno/config.h", "Pins, speeds, thresholds", "Defaults match the wiring"]))
beat(4, "Wi-Fi name and password", "In the camera sketch you can change the Wi-Fi name and password at the top. Keep the password at least eight characters long.",
     right=code(['#define WIFI_SSID     "ResQBot-01"', '#define WIFI_PASSWORD "rescue123"   // at least 8 characters', '#define CAM_URL       "http://192.168.4.1"', "#define LINK_RX 13", "#define LINK_TX 14"], hl=(0, 1)),
     left=bullets(["ResQCam_Gateway.ino, top of the file", "Change the name and password if you like"]))
beat(4, "Uno: unplug D0 first", "To program the Uno, first unplug the wire on D0 and switch the robot off. D0 is shared with the USB connection, so uploads fail while the camera is connected.",
     left=card("🔌", "Unplug the D0 wire", "Plug it back in after the upload.", "warn"), right=wire(650, 190, 800, 90))
beat(4, "Upload to the Uno", "Connect the Uno by USB, open ResQBot_Uno.ino, choose Arduino Uno as the board and your COM port, and click Upload.",
     right=ide("ResQBot_Uno | Arduino IDE 2", ["Tools", "Board", "Arduino AVR Boards", "Arduino Uno"], '<div class="item"><b>Board</b> Arduino Uno</div><div class="item"><b>Port</b> COM5 (Arduino Uno)</div><div class="btns"><span class="go">→ Upload</span></div><p class="note">Done uploading. Sketch uses 64 % of program storage.</p>'),
     left=bullets(["Open ResQBot_Uno.ino", "Board: Arduino Uno", "Port: your COM port", "Click Upload"]), cap="Connect the Uno by USB, open ResQBot_Uno.ino, choose Arduino Uno as the board and your COM port, and click Upload.")
beat(4, "Check the Uno's output", "Open the Serial Monitor at 115200 baud. Every 0.4 seconds you should see a line starting with S and a curly bracket. That is exactly what the camera board receives. Then close the monitor and plug D0 back in.",
     right=ide("Serial Monitor · 115200 baud", ["Tools", "Serial Monitor"], '<div class="term">E,info,0,Robot ready, thermal sensor OK<br>S{"mode":"manual","state":"manual control","uptime":1,"object":27.9,<br>&nbsp;"airTemp":29.0,"humidity":64,"distance":118,"gas":212, …}<br>S{"mode":"manual","state":"manual control","uptime":2, …}</div>'),
     left=bullets(["Tools → Serial Monitor", "Baud: 115200", "Lines start with S{ …", "Close it, reconnect D0"]))
beat(4, "Camera board on its programmer", "Now the ESP32-CAM. Take it off the robot, plug it onto the ESP32-CAM-MB programmer board, and connect it by micro USB.",
     left=bullets(["ESP32-CAM onto the MB board", "Micro-USB to the computer"]), right=card("📷", "ESP32-CAM + MB board", "The MB board adds USB and the IO0 / RST buttons for programming."))
beat(4, "Upload to the ESP32-CAM", "Open ResQCam_Gateway.ino, choose AI Thinker ESP32-CAM, and click Upload. If it stops at waiting for download, hold the IO0 button, tap RST, and let go.",
     right=ide("ResQCam_Gateway | Arduino IDE 2", ["Tools", "Board", "esp32", "AI Thinker ESP32-CAM"], '<div class="item"><b>Board</b> AI Thinker ESP32-CAM</div><div class="item"><b>Port</b> COM7</div><div class="btns"><span class="go">→ Upload</span></div><p class="note">Stuck on "waiting for download"? Hold IO0, tap RST, release.</p>'),
     left=bullets(["Open ResQCam_Gateway.ino", "Board: AI Thinker ESP32-CAM", "Click Upload", "Stuck? Hold IO0, tap RST"]), cap="Open ResQCam_Gateway.ino, choose AI Thinker ESP32-CAM, and click Upload. If it stops at “waiting for download”, hold IO0, tap RST and let go.")
beat(4, "Camera board is ready", "Press RST. The Serial Monitor shows the Wi-Fi name and the address, 192.168.4.1. Now put the camera back on the robot.",
     right=ide("Serial Monitor · 115200 baud", ["Tools", "Serial Monitor"], '<div class="term">Wi-Fi "ResQBot-01" -&gt; http://192.168.4.1  (video :81/stream)</div>'),
     left=bullets(["Press RST", "Address: 192.168.4.1", "Move the camera back onto the robot"]))

# 5 first test
beat(5, "Power on", "Switch the robot on. The Uno gives two short beeps and the servos center. That means it is ready.",
     left=card("🔔", "Two short beeps = ready", "The pan-tilt head centres and looks straight ahead.", "ok"), right=sch(1, 30, 940, 700, 150))
beat(5, "Join the robot's Wi-Fi", "On your phone, join the Wi-Fi called ResQBot-01. The password is rescue123. Android will say the network has no internet. Tap Keep connected.",
     right='<div class="phone"><div class="pbar">Wi-Fi</div><div class="net on">ResQBot-01 <span>Connected, no internet</span></div><div class="net">Home Wi-Fi</div><div class="toast">This network has no internet access. Stay connected? <b>Keep connected</b></div></div>',
     left=bullets(["Wi-Fi: ResQBot-01", "Password: rescue123", "“No internet” → Keep connected"]))
beat(5, "Open the dashboard", "Open a browser and go to 192.168.4.1. The dashboard opens, the status pill at the top turns LIVE, and the camera panel shows the live video.",
     right=crop(PHONE, 0, 0, 1040, 1500), left=bullets(["Browser → 192.168.4.1", "Status pill: LIVE", "Camera panel: live video"]))
beat(5, "Check every sensor", "Check each sensor tile. Hold your hand in front of the thermal sensor and the IR reading rises. The air tile shows the DHT11's temperature and humidity within five seconds.",
     right=crop(DASH, 25, 1378, 1180, 700), left=bullets(["IR ahead rises near your hand", "Air · DHT11: °C and humidity", "Wait 5 s for the first DHT11 reading"]))
beat(5, "Distance and motion", "Move your hand in front of the ultrasonic sensor and the obstacle distance changes. After 30 seconds, the motion tile starts reacting to movement.",
     right=crop(DASH, 25, 1378, 1180, 700), left=bullets(["Obstacle changes with your hand", "Motion works after 30 s warm-up", "Smoke/gas should say clear"]))

# 6 dashboard
beat(6, "The thermal radar", "Here is the dashboard. The thermal radar shows the last sweep. The inner ring is the floor and the outer ring is eye level. Warm areas turn yellow and red.",
     right=crop(DASH, 25, 462, 1180, 890), left=bullets(["Inner ring: floor row", "Outer ring: level row", "Warm = yellow and red", "! marks the target"]))
beat(6, "Driving", "In Manual mode, hold the arrow buttons to drive. The robot only moves while your finger is down, and it stops on its own if the phone goes quiet.",
     right=crop(DASH, 1231, 1378, 940, 700), left=bullets(["Manual mode", "Hold an arrow to drive", "Lift your finger: it stops", "Laptop: W A S D keys"]))
beat(6, "Thermal scan", "Tap Thermal scan and the sensor head sweeps 140 degrees in about five seconds. Stand in front of it, and your body heat appears on the radar in your direction.",
     right=crop(DASH, 25, 462, 1180, 890), left=bullets(["Tap Thermal scan", "≈ 5 s, 30 readings", "Your heat shows at your bearing"]))
beat(6, "Auto search", "Auto search makes the robot hunt on its own. It drives, avoids obstacles, stops to scan, and turns toward any body-like heat.",
     right=crop(DASH, 25, 126, 2147, 330), left=bullets(["Tap Auto search", "Drive, avoid, scan, repeat", "Turns toward body-like heat"]))
beat(6, "How it decides", "When it finds something, it creeps to 35 cm, waits five seconds, and scores the clues from 0 to 100: heat contrast, size, getting warmer up close, and movement.",
     right=full(FLOW), left=bullets(["Approach to 35 cm", "Wait 5 s", "Score 0–100 from four clues", "Movement is a bonus, not required"]))
beat(6, "Survivor alert", "At 60 or more, it raises a survivor alert. The robot parks next to the person with a flashing beacon and buzzer, and your phone shows the temperature, the distance, and whether the person is moving.",
     right=crop(DASH, 25, 126, 2147, 230), left=bullets(["Score ≥ 60 → alert", "Beacon + buzzer at the person", "Phone shows °C, distance, moving or not"]))
beat(6, "Acknowledge and log", "Tap Acknowledge once the rescue team has the location, and the robot resumes searching. The event log records every detection and hazard, and you can download it as a CSV file for your report.",
     right=crop(DASH, 25, 2099, 1180, 440), left=bullets(["Acknowledge → search resumes", "Event log with times", "Download CSV for the report"]))
beat(6, "E-STOP and camera tools", "E-STOP stops everything instantly, from any state. Use Take photo to save evidence, and Flash light to light up dark spaces.",
     right=crop(DASH, 1231, 462, 940, 890), left=bullets(["E-STOP: always one tap away", "Take photo: saves a JPEG", "Flash light: lights dark voids"]))

# 7 calibration
beat(7, "Turn rate", "Calibrate a few values in config.h for your robot. First, the turn rate. Spin on the spot for three seconds, measure the angle, divide by three, and set TURN_DEG_PER_SEC.",
     right=code(["#define TURN_DEG_PER_SEC   120.0   // degrees turned in 1 s"], hl=(0,)), left=bullets(["Spin for 3 s", "Measure the angle", "Angle ÷ 3 → TURN_DEG_PER_SEC"]))
beat(7, "Gas alarm", "For the gas alarm, let the MQ-2 warm up for three minutes in clean air, note the gas value on the dashboard, and set GAS_ALARM_RAW about 40 percent higher.",
     right=code(["#define GAS_ALARM_RAW    400   // clean-air value + 40 %"], hl=(0,)), left=bullets(["Warm up 3 min in clean air", "Read the gas value", "+40 % → GAS_ALARM_RAW"]))
beat(7, "Battery reading", "Compare the dashboard's battery voltage with your multimeter, and adjust BATTERY_ADC_CAL until they match.",
     right=code(["#define BATTERY_ADC_CAL  1.00   // meter ÷ dashboard"], hl=(0,)), left=bullets(["Measure the pack with a meter", "Meter ÷ dashboard → BATTERY_ADC_CAL"]))
beat(7, "Thermal tuning", "If the radar is noisy in an empty room, raise DELTA_MIN_C to 2. Adjust TILT_ANGLES so the lower row looks at the floor about a metre ahead. Upload the Uno again after each change.",
     right=code(["#define DELTA_MIN_C      1.5    // raise to 2.0 if noisy", "static const int TILT_ANGLES[2] = {70, 95};   // floor, level"], hl=(0, 1)),
     left=bullets(["Noisy radar → DELTA_MIN_C 2.0", "Lower row: floor ~1 m ahead", "Re-upload after each change"]))

# 8 troubleshooting
beat(8, "Arduino not responding", "If the dashboard says Arduino not responding, check the link: Uno D1 through the divider to IO13, and IO14 to D0. Transmit always goes to receive. And check the common ground.",
     right=sch(6, 1130, 170, 500, 330), left=bullets(["D1 → 1 kΩ → IO13", "IO14 → D0", "Common GND", "Unplug the Uno's USB cable"]))
beat(8, "Upload problems", "If the Uno upload fails with not in sync, the D0 wire is still connected. Unplug it while uploading. If the camera upload hangs, use the IO0 and RST buttons.",
     right=table([["Problem", "Fix"], ["Uno: not in sync", "Unplug D0, robot off"], ["CAM: waiting for download", "Hold IO0, tap RST"], ["No COM port", "Try another USB cable"]]),
     left=bullets(["Uno: unplug D0", "Camera: IO0 + RST", "Use a data USB cable"]), cap="If the Uno upload fails with “not in sync”, the D0 wire is still connected. If the camera upload hangs, use the IO0 and RST buttons.")
beat(8, "Camera and sensor problems", "If the camera restarts when the flash turns on, enlarge the capacitor at its power pins and keep its power wires short. If a sensor says not responding, check its data wires: A4 and A5 for the thermal sensor, D2 for the DHT11.",
     right=table([["Banner", "Check"], ["Camera offline / resets", "220–470 µF at camera, short wires"], ["Thermal sensor not responding", "SDA A4, SCL A5"], ["DHT11 not responding", "DATA on D2, pull-up"], ["Wrong motor direction", "Swap that pair's wires"]]),
     left=bullets(["Camera: bigger capacitor", "MLX90614: A4 / A5", "DHT11: D2", "Motors: swap the pair"]))

# outro
beat(8, "Stay safe", "A final word on safety. Charge the Li-ion pack only with a proper two-cell charger, never leave it charging unattended, and remember that the robot is a scout. A no-survivor result never clears a space on its own.",
     left=card("🛟", "The robot is a scout", "It helps rescuers decide where to look. It does not replace them.", "warn"),
     right=bullets(["Charge with a 2S (8.4 V) charger only", "Never charge unattended", "Not for explosive atmospheres", "E-STOP is always available"]))
beat(8, "You're ready", "Everything shown here is in the setup guide and the schematics PDF. Good luck with the build, and with the competition.",
     left=bullets(["ResQBot_Setup_Guide.pdf", "ResQBot_Schematics.pdf", "ResQBot_Components.pdf"]), right=full(DASH, (1010, 740)))

# ---------------- render ----------------
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1920px;height:1080px;background:#0f161c;color:#e8edf4;font-family:'Segoe UI',Arial,sans-serif;overflow:hidden;position:relative}
.top{position:absolute;left:90px;right:90px;top:34px;display:flex;align-items:center;gap:18px}
.chap{font:700 22px 'Bahnschrift','Segoe UI';letter-spacing:3px;text-transform:uppercase;color:#ff7b33}
.steps{margin-left:auto;display:flex;gap:8px}
.steps span{font:600 15px 'Segoe UI';padding:6px 12px;border-radius:99px;background:#17212a;color:#6f7f8f;border:1px solid #27343f}
.steps span.on{background:#ff7b33;color:#1a0a00;border-color:#ff7b33}
.steps span.done{color:#c9d3dd}
h1{position:absolute;left:90px;top:100px;width:680px;font:700 58px/1.04 'Bahnschrift','Segoe UI';text-transform:uppercase;letter-spacing:.5px}
.full h1{width:1700px}
.left{position:absolute;left:90px;top:300px;width:680px}
.right{position:absolute;left:820px;top:120px;width:1010px;height:740px;display:flex;align-items:center;justify-content:center}
ul{list-style:none;display:grid;gap:18px}
li{font-size:31px;line-height:1.25;padding-left:38px;position:relative;color:#dbe3ea}
li::before{content:"";position:absolute;left:0;top:13px;width:16px;height:16px;border-radius:4px;background:#ff7b33}
li.hl{color:#fff;font-weight:700}
.right ul li{font-size:34px}
.crop{position:relative;overflow:hidden;background:#fff;border-radius:18px;box-shadow:0 30px 70px -30px rgba(0,0,0,.8)}
.crop img{position:absolute;max-width:none}
.cap{position:absolute;left:90px;right:90px;bottom:36px;min-height:118px;background:#17212a;border:1px solid #27343f;border-radius:18px;
 padding:20px 30px;font-size:31px;line-height:1.35;color:#fff;display:flex;align-items:center}
.callout{display:flex;gap:26px;align-items:flex-start;background:#17212a;border:2px solid #27343f;border-radius:20px;padding:30px;width:100%}
.callout .ic{font-size:64px;line-height:1}
.callout b{font:700 40px/1.1 'Bahnschrift','Segoe UI';display:block;margin-bottom:10px}
.callout p{font-size:27px;color:#b9c5d0;line-height:1.35}
.callout.warn{border-color:#ffb020;background:#2a2110}.callout.ok{border-color:#2ec4a6;background:#0f2a24}.callout.accent{border-color:#ff7b33}
.right .callout{width:900px}
.win{width:980px;background:#1b2530;border:1px solid #33414e;border-radius:16px;overflow:hidden;box-shadow:0 30px 70px -30px rgba(0,0,0,.8)}
.win .bar{display:flex;gap:9px;align-items:center;padding:14px 18px;background:#121a21}
.win .bar i{width:13px;height:13px;border-radius:50%;background:#3a4754}.win .bar b{margin-left:14px;font:600 19px 'Segoe UI';color:#9fb0bf}
.crumbs{padding:16px 24px;font:600 24px 'Segoe UI';color:#ffb27a;background:#202c38;border-bottom:1px solid #33414e}
.crumbs span{color:#6f7f8f;margin:0 6px}
.wbody{padding:26px 28px;display:grid;gap:16px;font-size:24px}
.wbody label{color:#9fb0bf;font-size:21px}
.field{background:#0f161c;border:2px solid #3a4754;border-radius:10px;padding:14px 18px;font:500 22px Consolas,monospace;color:#e8edf4;word-break:break-all}
.field.hl{border-color:#ff7b33}.field.big{font:700 30px 'Segoe UI'}
.item{display:flex;gap:18px;align-items:center;background:#0f161c;border-radius:10px;padding:16px 18px;color:#dbe3ea}
.item.dim{opacity:.6}.item span{color:#9fb0bf;margin-left:auto}
.go{background:#2ec4a6;color:#062a22 !important;font-weight:800;padding:8px 16px;border-radius:8px;margin-left:12px}
.btns{display:flex;gap:14px;justify-content:flex-end}.btns span{padding:9px 18px;border-radius:8px;background:#2a3642;color:#cbd5df}
.dialog{background:#2a2110;border:1px solid #ffb020;border-radius:10px;padding:16px 18px;display:flex;align-items:center;gap:10px}
.note{color:#9fb0bf;font-size:20px}
.term{background:#05090c;border-radius:10px;padding:18px;font:500 20px/1.6 Consolas,monospace;color:#7ee2b8}
.code{width:1000px;background:#0a1015;border:1px solid #27343f;border-radius:16px;padding:22px 0;font:500 24px/1.55 Consolas,monospace;color:#cfe0ee}
.code .ln{padding:2px 26px;white-space:pre}.code .ln span{display:inline-block;width:46px;color:#4c5b68}
.code .ln.hl{background:#3a2210;color:#ffd2b0;border-left:5px solid #ff7b33}
.tbl{border-collapse:collapse;width:940px;font-size:26px;background:#17212a;border-radius:14px;overflow:hidden}
.tbl th{background:#ff7b33;color:#1a0a00;text-align:left;padding:14px 18px}.tbl td{padding:13px 18px;border-top:1px solid #27343f;color:#dbe3ea}
.phone{width:440px;height:700px;background:#f4f6f8;border:14px solid #222;border-radius:44px;padding:26px 20px;color:#14202b;display:grid;gap:14px;align-content:start}
.pbar{font:700 30px 'Segoe UI'}
.net{background:#fff;border-radius:14px;padding:18px;font:600 24px 'Segoe UI';display:grid}.net span{font:400 18px 'Segoe UI';color:#2b8a3e}
.net.on{border:2px solid #2b8a3e}
.toast{margin-top:40px;background:#14202b;color:#fff;border-radius:16px;padding:20px;font-size:20px;line-height:1.4}.toast b{display:block;color:#ff9f5a;margin-top:10px;font-size:24px}
"""


def page(b, i):
    steps = "".join(f'<span class="{"on" if k == b["ch"] else "done" if k < b["ch"] else ""}">{c}</span>' for k, c in enumerate(CHAPTERS))
    label = f"Step {b['ch']} · {CHAPTERS[b['ch']]}" if b["ch"] else "ResQBot Mini · walkthrough"
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body class="{b['layout']}">
<div class="top"><div class="chap">{label}</div><div class="steps">{steps}</div></div>
<h1>{html.escape(b['title'])}</h1>
<div class="left">{b['left']}</div><div class="right">{b['right']}</div>
<div class="cap">{html.escape(b['cap'])}</div></body></html>"""


def render_slides():
    BUILD.mkdir(parents=True, exist_ok=True)
    procs = []
    for i, b in enumerate(B):
        h = BUILD / f"s{i:03d}.html"
        h.write_text(page(b, i), encoding="utf-8")
        png = BUILD / f"s{i:03d}.png"
        procs.append(subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                                       "--window-size=1920,1080", f"--user-data-dir=E:/tools/edge-shot-{i % 4}", f"--screenshot={png}", h.as_uri()],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        if len(procs) >= 4:
            for p in procs: p.wait()
            procs = []
    for p in procs: p.wait()
    print("slides:", len(B))


def tts():
    from kokoro_onnx import Kokoro
    k = Kokoro(str(KOKORO / "kokoro-v1.0.onnx"), str(KOKORO / "voices-v1.0.bin"))
    durs = []
    for i, b in enumerate(B):
        samples, sr = k.create(spoken(b["say"]), voice=VOICE, speed=SPEED, lang="en-us")
        pad = np.zeros(int(sr * 0.55), dtype=np.float32)
        audio = np.concatenate([np.zeros(int(sr * 0.25), dtype=np.float32), samples, pad])
        pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
        with wave.open(str(BUILD / f"s{i:03d}.wav"), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())
        durs.append(len(audio) / sr)
        print(f"voice {i + 1}/{len(B)} {durs[-1]:.1f}s", flush=True)
    (BUILD / "durations.json").write_text(json.dumps(durs))
    return durs


def assemble(durs):
    lst = []
    for i, d in enumerate(durs):
        seg = BUILD / f"s{i:03d}.mp4"
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(BUILD / f"s{i:03d}.png"),
                        "-i", str(BUILD / f"s{i:03d}.wav"), "-t", f"{d:.3f}", "-c:v", "libx264", "-preset", "medium", "-tune", "stillimage",
                        "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", str(seg)], check=True)
        lst.append(f"file '{seg.as_posix()}'")
    (BUILD / "list.txt").write_text("\n".join(lst))
    out = OUT / "ResQBot_Setup_Walkthrough.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(BUILD / "list.txt"),
                    "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
    print("video:", out, f"{sum(durs) / 60:.1f} min")


if __name__ == "__main__":
    render_slides()
    if "--only-slides" in sys.argv:
        sys.exit()
    assemble(tts())
