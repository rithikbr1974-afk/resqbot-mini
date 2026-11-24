"""Builds docs/bom/ResQBot_Components.html (and the PDF via build_pdf.ps1) from the parts table below.

Prices were read from the store pages on 9 Oct 2026 (incl. GST, shipping extra). Stock changes daily.
"""
from html import escape
from pathlib import Path

CHECKED = "9 October 2026"

# group, part, what it does, qty, unit price, store, url, stock, alternative (text, price, url) or None
PARTS = [
    ("Brain and camera", [
        ("Arduino Uno R3 (CH340 compatible)", "Main board: reads every sensor, runs the search, drives motors and servos", 1, 249,
         "Robu.in", "https://robu.in/product/arduino-uno-r3-ch340g-atmega328p-devlopment-board/", "You have it",
         ("Robu: Arduino Uno R3 with cable", 424, "https://robu.in/product/arduino-uno-r3/")),
        ("ESP32-CAM board with OV2640 2 MP camera", "Live video, Wi-Fi hotspot and the dashboard; gets all data from the Uno", 1, 846,
         "Amazon.in", "https://www.amazon.in/dp/B0HHWXTY3L", "You have it",
         ("Amazon: ESP32-CAM with camera (4.1 stars)", 999, "https://www.amazon.in/dp/B0BXGWCL91")),
        ("ESP32-CAM-MB USB programmer board", "Uploads code to the ESP32-CAM (skip if your camera listing includes it)", 1, 119,
         "Robu.in", "https://robu.in/product/esp32-cam-mb-micro-usb-shield-module-for-esp32-cam-development-board/", "In stock",
         ("Amazon: ESP32-CAM-MB", 214, "https://www.amazon.in/dp/B0GGDDXNQR")),
    ]),
    ("Sensors", [
        ("MLX90614 IR temperature sensor (GY-906)", "Body-heat detection: the 'thermal camera' on the pan-tilt head", 1, 759,
         "Amazon.in", "https://www.amazon.in/dp/B0GV4FYYVD", "In stock",
         ("Robu: SmartElex MLX90614 ESF module (in stock)", 977,
          "https://robu.in/product/smartelex-mlx90614-esf-ir-non-contact-temp-sensor-module/")),
        ("HC-SR04 ultrasonic distance sensor", "Obstacle avoidance and stopping 35 cm from a person", 1, 79,
         "Robu.in", "https://robu.in/product/hc-sr04-ultrasonic-range-finder/", "In stock", None),
        ("HC-SR501 PIR motion sensor", "Detects whether the survivor is moving", 1, 69,
         "Robu.in", "https://robu.in/product/pir-motion-sensor-detector-module-hc-sr501/", "In stock", None),
        ("DHT11 temperature and humidity module", "Air temperature and humidity next to the IR readings", 1, 59,
         "Robu.in", "https://robu.in/product/dht11-digital-relative-humidity-temperature-sensor-module/", "In stock",
         ("Robu: SmartElex DHT11 module", 170, "https://robu.in/product/smartelex-dht11-temp-humidity-sensor-module/")),
        ("MQ-2 smoke / gas sensor module (Winsen)", "Smoke and LPG warning for rescuers", 1, 129,
         "Robu.in", "https://robu.in/product/winsen-mq-2-smoke-sensor/", "In stock",
         ("Amazon: Prakti MQ-2 module", 140, "https://www.amazon.in/dp/B09XTK79D4")),
    ]),
    ("Drive and thermal head", [
        ("4WD robot car chassis kit (2 plates, 4 BO motors, 4 wheels, screws)", "Robot body and wheels", 1, 609,
         "Amazon.in", "https://www.amazon.in/dp/B077GNR6WQ", "In stock",
         ("Robu: Cligo 4WD ABS chassis, frame only (add 4 BO motors ₹82 + 4 wheels ₹29)", 749,
          "https://robu.in/product/cligo-4wd-abs-smart-robot-car-chassis/")),
        ("L298N dual motor driver module", "Drives the left and right motor pairs", 1, 129,
         "Robu.in", "https://robu.in/product/l298n-2a-based-motor-driver-module-good-quality/", "In stock", None),
        ("TowerPro SG90 micro servo", "Pan and tilt of the thermal sensor", 2, 89,
         "Robu.in", "https://robu.in/product/towerpro-sg90-9g-mini-servo-9-gram/", "In stock",
         ("Robu: SG90 'good quality' version", 185,
          "https://robu.in/product/towerpro-sg90-9gm-1-2kg-180-degree-rotation-servo-motor-good-quality/")),
        ("2-axis pan-tilt bracket for SG90", "Holds the thermal sensor on the two servos", 1, 89,
         "Robu.in", "https://robu.in/product/2-axis-pan-tilt-camera-mount-camerasensors-servo-sg90s-mg90s/", "In stock", None),
    ]),
    ("Power", [
        ("7.4 V 2500 mAh 2S Li-ion pack, protected, with DC jack", "Powers everything; built-in protection board", 1, 579,
         "Robu.in", "https://robu.in/product/18650-li-ion-2500mah-7-4v-2s1p-protected-battery-pack-3c-2/", "In stock",
         ("Robu: 2 × BAK 18650 cells (₹229 each) + 2-cell holder (₹59), no protection board", 517,
          "https://robu.in/product/bak-nmc-18650-2600mah-3c-lithium-ion-3-6v-battery/")),
        ("5.5 mm DC jack, male, with wire", "Connects the battery pack to the robot", 1, 29,
         "Robu.in", "https://robu.in/product/5mm-dc-jack-male-connector-with-wire/", "In stock", None),
        ("LM2596 buck converter (step-down)", "Clean 5 V for the ESP32, camera, servos and sensors", 1, 98,
         "Amazon.in", "https://www.amazon.in/dp/B0BHNTGF23", "In stock",
         ("Robu: LM2596S module (out of stock today)", 49, "https://robu.in/product/lm2596s-dc-dc-buck-converter-power-supply/")),
        ("Mini rocker switch, 2-pin (pack of 2)", "Main power ON/OFF", 1, 30,
         "Amazon.in", "https://www.amazon.in/dp/B0H6F78F97", "In stock",
         ("Robu: KCD1 rocker switch (in stock)", 105, "https://robu.in/product/kcd1-12v-24v-on-off2-pin-rocker-switch/")),
    ]),
    ("Alerts and small parts", [
        ("5 V active buzzer", "Alert sound and call-out beep", 1, 18,
         "Robu.in", "https://robu.in/product/5v-active-electromagnetic-buzzer-pack-of-5/", "In stock", None),
        ("BC547 NPN transistor (Q1, Q2)", "Switch the buzzer and the beacon LED from Uno pins", 2, 3,
         "Robu.in", "https://robu.in/product/bc547-npn-transistor-pack-of-20/", "In stock", None),
        ("Bright 5 mm Piranha LED", "Beacon light that marks the survivor", 1, 29,
         "Robu.in", "https://robu.in/product/5mm-piranha-4pin-led-warm-white/", "In stock", None),
        ("Resistors ¼ W: 1 kΩ ×3, 2 kΩ, 10 kΩ ×3, 100 Ω (R1–R8)",
         "Serial-link and battery dividers, transistor bases, LED current, DHT pull-up", 1, 10,
         "Local shop", "", "≈ ₹1 each",
         ("Robu: 1500-piece resistor kit, 75 values (for a lab)", 489,
          "https://robu.in/product/pro-range-new-1500pcs-75-kinds-specifications-x-20pcs-1-4w-metal-film-resistor-pack-error-1-common-component-package/")),
        ("Capacitors, diode, fuse: 470 µF + 220 µF 10 V, 4 × 100 nF, 1N4148, 3 A fuse + inline holder",
         "C1–C6, D1, F1 from the schematic: power filtering and protection", 1, 40,
         "Local shop", "", "≈ ₹40", None),
    ]),
    ("Wiring and mounting", [
        ("Jumper wires, male–female, 40 pcs, 30 cm", "Module connections", 1, 69,
         "Robu.in", "https://robu.in/product/male-to-female-jumper-wires-40-pin-30cm/", "In stock", None),
        ("Jumper wires, female–female, 40 pcs, 20 cm", "Module-to-ESP32 connections", 1, 49,
         "Robu.in", "https://robu.in/product/20cm-dupont-wire-color-jumper-cable-2-54mm-1p-1p-female-female-40pcs/", "In stock", None),
        ("Zero PCB (general-purpose board)", "Base for the ESP32, dividers and transistor", 1, 91,
         "Amazon.in", "https://www.amazon.in/dp/B0C3B8CGG8", "In stock", None),
        ("Female berg strip 1×40 (pack of 5)", "Plug-in sockets so the ESP32 is removable", 1, 98,
         "Robu.in", "https://robu.in/product/1-40-pin-2-54m-straight-long-female-berg-strip-connector-pack-of-5/", "In stock",
         ("Local shop: one 1×40 strip", 15, "")),
        ("M3 × 10 mm bolt and nut set (25 pcs)", "Mounting the modules on the chassis", 1, 78,
         "Robu.in", "https://robu.in/product/easymech-m3-x-10mm-chhd-bolt-nut-and-washer-set-25-pcs/", "In stock", None),
        ("Black heat-shrink tube kit (127 pcs)", "Insulating joints; a 10 mm piece is the IR viewing tube", 1, 146,
         "Robu.in", "https://robu.in/product/127pcs-black-heat-shrinkable-tube-kit-plastic-bag/", "In stock", None),
    ]),
]

ONE_TIME = [
    ("2S Li-ion charger, 8.4 V 2 A, DC plug", "Charges the battery pack safely (needed once)", 549,
     "Robu.in", "https://robu.in/product/pro-range-battery-charger-2s-li-ion-8-4v-2a-with-dc-5-5mm-2-5mm-male-plug/"),
    ("USB data cable (micro-USB for most ESP32 boards)", "Uploading code; any phone data cable works", 0, "Already owned", ""),
    ("Soldering iron, solder, multimeter, glue gun, screwdriver", "Assembly tools, usually available in a college lab", 0, "Lab", ""),
]

OWNED = {"Arduino Uno R3 (CH340 compatible)", "ESP32-CAM board with OV2640 2 MP camera"}


def rupees(v):
    return f"₹{v:,.0f}"


def main():
    rows, total, cam = [], 0, 0
    n = 0
    for group, parts in PARTS:
        rows.append(f'<tr class="grp"><td colspan="7">{escape(group)}</td></tr>')
        for name, why, qty, price, store, url, stock, alt in parts:
            n += 1
            line = qty * price
            total += line
            if name in OWNED:
                cam += line
            link = f'<a href="{url}">{escape(store)}</a>' if url else escape(store)
            alt_html = ""
            if alt:
                at, ap, au = alt
                at_html = f'<a href="{au}">{escape(at)}</a>' if au else escape(at)
                alt_html = f'<div class="alt">Alternative: {at_html} — {rupees(ap)}</div>'
            rows.append(
                f"<tr><td class='n'>{n}</td><td><b>{escape(name)}</b><div class='why'>{escape(why)}</div>{alt_html}</td>"
                f"<td class='c'>{qty}</td><td class='r'>{rupees(price)}</td><td class='r'><b>{rupees(line)}</b></td>"
                f"<td>{link}</td><td class='s'>{escape(stock)}</td></tr>")
    rows.append(f'<tr class="total"><td></td><td>Total — full robot ({n} items)</td><td></td><td></td>'
                f'<td class="r">{rupees(total)}</td><td colspan="2"></td></tr>')

    once = "".join(
        f"<tr><td><b>{escape(a)}</b><div class='why'>{escape(b)}</div></td><td class='r'>{rupees(p) if p else '—'}</td>"
        f"<td>{f'<a href={chr(34)}{u}{chr(34)}>{escape(s)}</a>' if u else escape(s)}</td></tr>"
        for a, b, p, s, u in ONE_TIME)

    no_cam = total - cam
    html = TEMPLATE.format(checked=CHECKED, rows="\n".join(rows), once=once, total=rupees(total),
                           no_cam=rupees(no_cam), cam=rupees(cam), n=n)
    out = Path(__file__).resolve().parent.parent / "docs" / "bom" / "ResQBot_Components.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(out, "total", total, "without camera", no_cam)


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>ResQBot Mini — Components and Shopping List</title>
<style>
@page {{ size: A4; margin: 15mm 13mm 17mm 13mm;
  @bottom-center {{ content: "ResQBot Mini · components list · page " counter(page); font: 8.5pt "Segoe UI", Arial; color: #8a94a6; }} }}
html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{ font: 9.6pt/1.45 "Segoe UI", Arial, sans-serif; color: #1d2433; margin: 0; }}
h1 {{ font-size: 21pt; margin: 0 0 1mm; }}
h2 {{ font-size: 13pt; margin: 7mm 0 2.5mm; }}
.sub {{ color: #5b6475; font-size: 10.5pt; margin-bottom: 5mm; }}
.head {{ display: flex; justify-content: space-between; align-items: flex-end; gap: 6mm; border-bottom: 3px solid #ff6b1a; padding-bottom: 3mm; margin-bottom: 4mm; }}
.stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 3mm; margin: 0 0 4mm; }}
.stat {{ background: #f6f8fb; border: 1px solid #dde3ec; border-radius: 3mm; padding: 3mm 4mm; }}
.stat b {{ display: block; font-size: 17pt; color: #ff6b1a; }}
.stat span {{ font-size: 8.8pt; color: #5b6475; }}
table {{ width: 100%; border-collapse: collapse; }}
th {{ background: #1d2433; color: #fff; text-align: left; padding: 2mm; font-weight: 600; font-size: 8.8pt; }}
td {{ padding: 1.8mm 2mm; border-bottom: 1px solid #e4e8ef; vertical-align: top; }}
tr {{ break-inside: avoid; }}
tr.grp td {{ background: #fff3eb; color: #b34700; font-weight: 800; font-size: 9pt; text-transform: uppercase; letter-spacing: .6px; padding: 1.6mm 2mm; }}
tr.total td {{ background: #1d2433; color: #fff; font-weight: 800; font-size: 10.5pt; }}
td.n {{ color: #8a94a6; width: 5mm; }}
td.c {{ text-align: center; }}
td.r, th.r {{ text-align: right; white-space: nowrap; }}
td.s {{ font-size: 8.4pt; color: #1b8a5a; white-space: nowrap; }}
.why {{ color: #5b6475; font-size: 8.6pt; }}
.alt {{ font-size: 8.3pt; color: #5b6475; margin-top: .8mm; }}
a {{ color: #1c5cab; text-decoration: none; }}
.box {{ background: #f6f8fb; border: 1px solid #dde3ec; border-radius: 3mm; padding: 3mm 4mm; margin: 3mm 0; break-inside: avoid; }}
.warn {{ background: #fff7e6; border-color: #f1c66a; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; }}
ul {{ margin: 1mm 0 0; padding-left: 5mm; }} li {{ margin-bottom: .8mm; }}
</style></head><body>
<div class="head">
  <div><h1>ResQBot Mini — Components &amp; Shopping List</h1>
  <div class="sub">Every part needed to build the robot, with a store link and today's price for each.</div></div>
  <div class="sub" style="text-align:right">Prices checked on {checked}<br>incl. GST · shipping extra</div>
</div>
<div class="stats">
  <div class="stat"><b>{total}</b><span>full robot incl. Uno and ESP32-CAM ({n} items, online prices)</span></div>
  <div class="stat"><b>{no_cam}</b><span>still to buy: you already have the Uno and ESP32-CAM ({cam})</span></div>
  <div class="stat"><b>₹549</b><span>one-time: battery charger (not part of the robot)</span></div>
</div>

<table>
<tr><th>#</th><th>Component</th><th>Qty</th><th class="r">Rate</th><th class="r">Amount</th><th>Buy link</th><th>Stock</th></tr>
{rows}
</table>

<h2>One-time items (not counted in the robot's cost)</h2>
<table>
<tr><th>Item</th><th class="r">Rate</th><th>Where</th></tr>
{once}
</table>

<div class="grid">
<div class="box"><b>Getting the cost under ₹3,000</b>
<ul>
  <li>Buy small parts (resistors, berg strip, switch, LED, buzzer, jumpers, zero PCB) at a local electronics market — usually cheaper than online.</li>
  <li>Use a black drinking straw or rolled black paper for the IR tube instead of the heat-shrink kit (−₹146).</li>
  <li>A 2WD chassis instead of 4WD usually saves ₹200–300; a single pan servo (no tilt) saves ₹89.</li>
  <li>Order everything from one store where you can: one shipping charge instead of several.</li>
</ul></div>
<div class="box warn"><b>Before you order</b>
<ul>
  <li>Online stock changes daily. If an item is out of stock, use the alternative link or any listing with the same part name.</li>
  <li>Main board is the Arduino Uno; the ESP32-CAM is the camera and Wi-Fi board. Wiring: docs/ResQBot_Schematics.pdf.</li>
  <li>Some ESP32-CAM listings already include the MB programmer board; then skip item 3.</li>
  <li>Check the chassis listing includes 4 motors and 4 wheels.</li>
  <li>Li-ion safety: charge only with a 2S (8.4 V) charger, never unattended.</li>
</ul></div>
</div>
</body></html>
"""

if __name__ == "__main__":
    main()
