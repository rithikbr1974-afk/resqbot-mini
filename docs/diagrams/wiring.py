"""Draws docs/diagrams/wiring.svg from the pin table below (keep it in step with firmware config.h)."""
from pathlib import Path

# Arduino Uno R3 headers (same order as the schematic, sheet 3)
LEFT = ["IOREF", "RESET", "3.3V", "5V", "GND", "GND ", "VIN", "A0", "A1", "A2", "A3", "A4/SDA", "A5/SCL"]
RIGHT = ["D0/RX", "D1/TX", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12", "D13", "GND  ", "AREF"]

C = {"motor": "#2a78d6", "sense": "#1baf7a", "i2c": "#ff6b1a", "servo": "#8b5cf6", "out": "#e5383b",
     "p5": "#d6336c", "p3": "#eda100", "gnd": "#1d2433", "link": "#0b7285"}

# pin -> (module, module pin, colour)
WIRES = {
    "5V": ("LM2596", "5 V out (+5V rail)", "p5"),
    "GND": ("common", "GND", "gnd"),
    "A0": ("MQ-2", "AO (direct)", "sense"),
    "A1": ("Battery +", "via 10k/10k divider", "sense"),
    "A2": ("HC-SR04", "TRIG", "sense"),
    "A3": ("HC-SR04", "ECHO (direct)", "sense"),
    "A4/SDA": ("MLX90614", "SDA", "i2c"),
    "A5/SCL": ("MLX90614", "SCL", "i2c"),
    "D0/RX": ("ESP32-CAM", "IO14 (TX)", "link"),
    "D1/TX": ("ESP32-CAM", "IO13 via 1k/2k", "link"),
    "D2": ("DHT11", "DATA", "sense"),
    "D3": ("Buzzer", "BC547 base via 1k", "out"),
    "D4": ("PIR HC-SR501", "OUT", "sense"),
    "D5": ("L298N", "ENA (remove jumper)", "motor"),
    "D6": ("L298N", "ENB (remove jumper)", "motor"),
    "D7": ("L298N", "IN1", "motor"),
    "D8": ("L298N", "IN2", "motor"),
    "D9": ("L298N", "IN3", "motor"),
    "D10": ("L298N", "IN4", "motor"),
    "D11": ("Servo PAN", "signal (orange)", "servo"),
    "D12": ("Servo TILT", "signal (orange)", "servo"),
    "D13": ("LED beacon", "BC547 base via 1k", "out"),
    "GND  ": ("common", "GND", "gnd"),
}

W, H = 1600, 1340
TOP, STEP = 210, 46
BX, BW = 650, 300
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
       'font-family="Segoe UI, Arial, sans-serif">',
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
       '<text x="40" y="54" font-size="28" font-weight="800" fill="#1d2433">ResQBot Mini — wiring (Arduino Uno main board + ESP32-CAM)</text>',
       '<text x="40" y="84" font-size="15" fill="#5b6475">Pins match firmware/ResQBot_Uno/config.h. All grounds are joined. '
       'Every sensor runs on 5 V; only Uno D1 → ESP32-CAM IO13 needs the 1k/2k divider.</text>']

# board
out.append(f'<rect x="{BX}" y="{TOP - 60}" width="{BW}" height="{STEP * 16 + 80}" rx="18" fill="#1d2433"/>')
out.append(f'<rect x="{BX + 95}" y="{TOP - 48}" width="110" height="34" rx="4" fill="#c9d1de"/>')
out.append(f'<text x="{BX + 150}" y="{TOP - 25}" text-anchor="middle" font-size="12" fill="#1d2433" font-weight="700">ARDUINO UNO</text>')
out.append(f'<rect x="{BX + 125}" y="{TOP + STEP * 16 - 4}" width="50" height="24" rx="3" fill="#8a94a6"/>')
out.append(f'<text x="{BX + 150}" y="{TOP + STEP * 16 + 36}" text-anchor="middle" font-size="12" fill="#c9d1de">USB</text>')

modules = {}
for side, pins in (("L", LEFT), ("R", RIGHT)):
    for i, pin in enumerate(pins):
        y = TOP + i * STEP
        px = BX if side == "L" else BX + BW
        used = pin in WIRES
        out.append(f'<circle cx="{px}" cy="{y}" r="7" fill="{"#ffffff" if used else "#5b6475"}" stroke="#c9d1de" stroke-width="2"/>')
        tx = px + 16 if side == "L" else px - 16
        anchor = "start" if side == "L" else "end"
        out.append(f'<text x="{tx}" y="{y + 5}" text-anchor="{anchor}" font-size="15" font-weight="700" '
                   f'fill="{"#ffffff" if used else "#6b7486"}">{pin}</text>')
        if not used:
            continue
        mod, mpin, col = WIRES[pin]
        colr = C[col]
        x2 = 470 if side == "L" else BX + BW + 180
        out.append(f'<line x1="{px}" y1="{y}" x2="{x2}" y2="{y}" stroke="{colr}" stroke-width="4" stroke-linecap="round"/>')
        lx = x2 - 12 if side == "L" else x2 + 12
        out.append(f'<text x="{lx}" y="{y + 5}" text-anchor="{"end" if side == "L" else "start"}" font-size="15" fill="#1d2433">'
                   f'<tspan font-weight="700">{mod}</tspan> <tspan fill="#5b6475">{mpin}</tspan></text>')

# power + notes panel
notes = [
    ("Power", "p5", ["2S pack (7.4 V) → fuse → switch → L298N +12V and LM2596 IN",
                     "LM2596 set to 5.0 V first → Uno 5V pin, ESP32-CAM 5V, all sensors,",
                     "servo red wires, buzzer +, LED (via 100 Ω). VIN not used.",
                     "All GNDs joined (battery −, L298N, LM2596, Uno, ESP32-CAM, sensors)"]),
    ("Motors", "motor", ["L298N OUT1/OUT2 → both LEFT motors in parallel",
                         "L298N OUT3/OUT4 → both RIGHT motors in parallel",
                         "If a side spins backwards, swap that side's two motor wires"]),
    ("ESP32-CAM link", "link", ["Uno D1 —1k— CAM IO13 —2k— GND   (5 V → 3.3 V)",
                                "CAM IO14 → Uno D0 directly · leave the SD slot empty",
                                "Unplug the D0 wire while uploading code to the Uno"]),
    ("Outputs", "out", ["Buzzer: D3 —1k— BC547 base; emitter GND; collector → buzzer −; buzzer + → 5 V",
                        "Beacon: D13 —1k— BC547 base; +5V —100 Ω— LED → collector; emitter GND"]),
]
panel_y, col_w = TOP + STEP * 16 + 50, 750
for i, (title, col, lines) in enumerate(notes):
    bx = 40 + (i % 2) * (col_w + 20)
    by = panel_y + (i // 2) * 150
    out.append(f'<rect x="{bx}" y="{by}" width="{col_w}" height="{40 + 25 * len(lines)}" rx="12" fill="#f6f8fb" stroke="#e1e6ee"/>')
    out.append(f'<circle cx="{bx + 22}" cy="{by + 24}" r="7" fill="{C[col]}"/>')
    out.append(f'<text x="{bx + 38}" y="{by + 30}" font-size="17" font-weight="800" fill="#1d2433">{title}</text>')
    for j, line in enumerate(lines):
        out.append(f'<text x="{bx + 20}" y="{by + 56 + 25 * j}" font-size="14.5" fill="#333b4a">{line}</text>')

Path(__file__).with_name("wiring.svg").write_text("\n".join(out) + "\n</svg>\n", encoding="utf-8")
