"""ResQBot Mini electrical schematics: 6 drawn sheets + netlist, as one printable HTML (-> PDF) and PNGs.

Run:  python docs/schematics/schematic.py   (then tools/build_pdf.ps1 on ResQBot_Schematics.html)
Arduino Uno main board + ESP32-CAM gateway. Pins and nets must match firmware/ResQBot_Uno/config.h.
"""
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
W, H = 1680, 1188
INK, WIRE, PWR, NETC, MUTED = "#1b1b1b", "#1f4e8c", "#b42318", "#6b21a8", "#5b6475"
SANS = "Segoe UI, Arial, sans-serif"
MONO = "Consolas, 'Courier New', monospace"
REV, DATE, BY = "2.0", "2026-10-18", "the user"


class Sheet:
    def __init__(self, num, title, subtitle=""):
        self.num, self.title, self.subtitle, self.p = num, title, subtitle, []

    def add(self, s):
        self.p.append(s)

    # ---------- basics ----------
    def line(self, x1, y1, x2, y2, color=INK, w=2):
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}" stroke-linecap="round"/>')

    def wire(self, *pts, dash=False):
        d = " ".join(f"{x},{y}" for x, y in pts)
        da = ' stroke-dasharray="9 7"' if dash else ""
        self.add(f'<polyline points="{d}" fill="none" stroke="{WIRE}" stroke-width="2.3" stroke-linejoin="round"{da}/>')

    def dot(self, x, y):
        self.add(f'<circle cx="{x}" cy="{y}" r="4.6" fill="{WIRE}"/>')

    def t(self, x, y, txt, size=14, anchor="start", color=INK, weight=400, mono=False):
        fam = MONO if mono else SANS
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{color}" '
                 f'font-weight="{weight}" font-family="{fam}">{escape(txt)}</text>')

    def lines(self, x, y, rows, size=13.5, gap=20, color=INK, mono=False):
        for i, r in enumerate(rows):
            self.t(x, y + i * gap, r, size=size, color=color, mono=mono)

    def nc(self, x, y):
        self.line(x - 6, y - 6, x + 6, y + 6, INK, 2)
        self.line(x - 6, y + 6, x + 6, y - 6, INK, 2)

    def panel(self, x, y, w, h, title):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#f8fafc" stroke="#d5dce5" stroke-width="1.5"/>')
        self.t(x + 16, y + 28, title, size=16, weight=700)

    # ---------- power symbols and net flags ----------
    def pwr(self, x, y, name):
        self.line(x, y, x, y - 16, PWR, 2.3)
        self.line(x - 14, y - 16, x + 14, y - 16, PWR, 3)
        self.t(x, y - 23, name, size=13, anchor="middle", color=PWR, weight=700)

    def gnd(self, x, y):
        self.line(x, y, x, y + 12, INK, 2.3)
        for dy, hw in ((12, 13), (17, 8), (22, 3)):
            self.line(x - hw, y + dy, x + hw, y + dy, INK, 2.3)

    def flag(self, x, y, name, side="right"):
        tw = len(name) * 7.4 + 14
        s = 1 if side == "right" else -1
        pts = [(x, y), (x + s * 9, y - 11), (x + s * (9 + tw), y - 11), (x + s * (9 + tw), y + 11), (x + s * 9, y + 11)]
        d = " ".join(f"{a},{b}" for a, b in pts)
        self.add(f'<polygon points="{d}" fill="#f6f0ff" stroke="{NETC}" stroke-width="1.6"/>')
        self.t(x + s * (9 + tw / 2), y + 4.5, name, size=12.5, anchor="middle", color=NETC, weight=600, mono=True)

    # ---------- components ----------
    def res(self, x, y, ref, val, orient="v"):
        if orient == "v":
            self.line(x, y, x, y + 20); self.line(x, y + 60, x, y + 80)
            self.add(f'<rect x="{x - 8}" y="{y + 20}" width="16" height="40" fill="#fff" stroke="{INK}" stroke-width="2"/>')
            self.t(x + 15, y + 38, ref, 13, weight=700); self.t(x + 15, y + 54, val, 13)
            return x, y + 80
        self.line(x, y, x + 20, y); self.line(x + 60, y, x + 80, y)
        self.add(f'<rect x="{x + 20}" y="{y - 8}" width="40" height="16" fill="#fff" stroke="{INK}" stroke-width="2"/>')
        self.t(x + 40, y - 14, ref, 13, "middle", weight=700); self.t(x + 40, y + 26, val, 13, "middle")
        return x + 80, y

    def cap(self, x, y, ref, val, pitch=60, polar=False):
        m = y + pitch / 2
        self.line(x, y, x, m - 4)
        self.line(x - 14, m - 4, x + 14, m - 4, INK, 3)
        if polar:
            self.add(f'<rect x="{x - 14}" y="{m + 3}" width="28" height="5" fill="{INK}"/>')
            self.t(x - 22, m - 8, "+", 13, "middle", weight=700)
            self.line(x, m + 8, x, y + pitch)
        else:
            self.line(x - 14, m + 4, x + 14, m + 4, INK, 3)
            self.line(x, m + 4, x, y + pitch)
        self.t(x + 20, m - 2, ref, 13, weight=700); self.t(x + 20, m + 14, val, 13)

    def diode(self, x, y, ref, val, pitch=60, cathode_top=True):
        m = y + pitch / 2
        self.line(x, y, x, m - 8); self.line(x, m + 8, x, y + pitch)
        if cathode_top:
            self.add(f'<polygon points="{x},{m - 8} {x - 11},{m + 8} {x + 11},{m + 8}" fill="#fff" stroke="{INK}" stroke-width="2"/>')
            self.line(x - 11, m - 8, x + 11, m - 8, INK, 2.5)
        else:
            self.add(f'<polygon points="{x - 11},{m - 8} {x + 11},{m - 8} {x},{m + 8}" fill="#fff" stroke="{INK}" stroke-width="2"/>')
            self.line(x - 11, m + 8, x + 11, m + 8, INK, 2.5)
        self.t(x + 18, m - 2, ref, 13, weight=700); self.t(x + 18, m + 14, val, 13)

    def led(self, x, y, ref, val, pitch=60):
        self.diode(x, y, "", "", pitch, cathode_top=False)
        m = y + pitch / 2
        for dy in (-6, 6):
            self.line(x + 13, m + dy - 2, x + 25, m + dy - 12, INK, 1.6)
            self.add(f'<polygon points="{x + 27},{m + dy - 14} {x + 20},{m + dy - 12} {x + 25},{m + dy - 7}" fill="{INK}"/>')
        self.t(x + 34, m - 2, ref, 13, weight=700); self.t(x + 34, m + 14, val, 13)

    def npn(self, x, y, ref, val):
        self.add(f'<circle cx="{x + 2}" cy="{y}" r="25" fill="#fff" stroke="{INK}" stroke-width="2"/>')
        self.line(x - 8, y - 15, x - 8, y + 15, INK, 3)
        self.line(x - 40, y, x - 8, y)
        self.line(x - 8, y - 7, x + 14, y - 22); self.line(x + 14, y - 22, x + 14, y - 40)
        self.line(x - 8, y + 7, x + 14, y + 22); self.line(x + 14, y + 22, x + 14, y + 40)
        self.add(f'<polygon points="{x + 14},{y + 22} {x + 2},{y + 21} {x + 9},{y + 12}" fill="{INK}"/>')
        self.t(x + 34, y - 4, ref, 13, weight=700); self.t(x + 34, y + 12, val, 13)
        return {"B": (x - 40, y), "C": (x + 14, y - 40), "E": (x + 14, y + 40)}

    def motor(self, x, y, ref, pitch=80):
        m = y + pitch / 2
        self.line(x, y, x, m - 20); self.line(x, m + 20, x, y + pitch)
        self.add(f'<circle cx="{x}" cy="{m}" r="20" fill="#fff" stroke="{INK}" stroke-width="2"/>')
        self.t(x, m + 6, "M", 17, "middle", weight=700)
        self.t(x - 26, m + 5, ref, 13, "end", weight=700)

    def buzzer(self, x, y, ref, val, pitch=80):
        m = y + pitch / 2
        self.line(x, y, x, m - 18); self.line(x, m + 18, x, y + pitch)
        self.add(f'<rect x="{x - 18}" y="{m - 18}" width="36" height="36" rx="18" fill="#fff" stroke="{INK}" stroke-width="2"/>')
        self.add(f'<path d="M{x - 9},{m + 7} Q{x},{m - 14} {x + 9},{m + 7}" fill="none" stroke="{INK}" stroke-width="2"/>')
        self.t(x - 26, m - 8, "+", 13, "middle", weight=700)
        self.t(x - 28, m + 10, ref, 13, "end", weight=700); self.t(x - 28, m + 26, val, 12, "end")

    def battery(self, x, y, ref, vals):
        self.line(x, y, x, y + 36); self.line(x, y + 68, x, y + 100)
        for yy, hw, w in ((36, 20, 2.5), (44, 10, 5), (60, 20, 2.5), (68, 10, 5)):
            self.line(x - hw, y + yy, x + hw, y + yy, INK, w)
        self.line(x, y + 46, x, y + 58, INK, 1.2)
        self.t(x + 22, y + 30, "+", 15, "middle", weight=700)
        self.t(x - 28, y + 56, ref, 13, "end", weight=700)
        for i, v in enumerate(vals):
            self.t(x - 70, y + 154 + i * 16, v, 12.5)

    def switch(self, x, y, ref, val):
        self.line(x, y, x + 24, y); self.line(x + 56, y, x + 80, y)
        for cx in (x + 24, x + 56):
            self.add(f'<circle cx="{cx}" cy="{y}" r="4" fill="#fff" stroke="{INK}" stroke-width="2"/>')
        self.line(x + 27, y - 2, x + 54, y - 18, INK, 2.3)
        self.t(x + 40, y - 28, ref, 13, "middle", weight=700); self.t(x + 40, y + 24, val, 12.5, "middle")

    def fuse(self, x, y, ref, val):
        self.line(x, y, x + 20, y); self.line(x + 60, y, x + 80, y)
        self.add(f'<rect x="{x + 20}" y="{y - 8}" width="40" height="16" fill="#fff" stroke="{INK}" stroke-width="2"/>')
        self.line(x + 20, y, x + 60, y, INK, 1.4)
        self.t(x + 40, y - 16, ref, 13, "middle", weight=700); self.t(x + 40, y + 26, val, 12.5, "middle")

    def module(self, x, w, ref, name, left=(), right=(), top=None, bottom=None, notes=(), title_inside=False, fill="#fffdf5"):
        """Box with pin stubs. left/right: list of (key, label, y). Returns {key: (x, y)} at the stub ends."""
        ys = [p[2] for p in list(left) + list(right)]
        top = top if top is not None else min(ys) - 52
        bottom = bottom if bottom is not None else max(ys) + 26 + 16 * len(notes)
        self.add(f'<rect x="{x}" y="{top}" width="{w}" height="{bottom - top}" rx="6" fill="{fill}" stroke="{INK}" stroke-width="2.2"/>')
        pins = {}
        for key, label, y in left:
            self.line(x - 30, y, x, y)
            self.t(x + 8, y + 5, label, 13, mono=True)
            pins[key] = (x - 30, y)
        for key, label, y in right:
            self.line(x + w, y, x + w + 30, y)
            self.t(x + w - 8, y + 5, label, 13, "end", mono=True)
            pins[key] = (x + w + 30, y)
        if title_inside:
            cx, cy = x + w / 2, (top + bottom) / 2 - 8 * len(notes)
            self.t(cx, cy, ref, 14, "middle", weight=700)
            self.t(cx, cy + 17, name, 12.5, "middle", color=MUTED)
            for i, n in enumerate(notes):
                self.t(cx, cy + 34 + i * 16, n, 12, "middle", color=MUTED)
        else:
            self.t(x + 10, top + 20, ref, 14, weight=700)
            self.t(x + 10, top + 37, name, 12.5, color=MUTED)
            for i, n in enumerate(notes):
                self.t(x + 10, bottom - 10 - (len(notes) - 1 - i) * 16, n, 12, color=MUTED)
        return pins

    def block(self, x1, x2, y, l1, l2):
        """Inline circuit block on a wire (overview sheet)."""
        self.add(f'<rect x="{x1}" y="{y - 16}" width="{x2 - x1}" height="32" rx="5" fill="#eef4ff" stroke="{WIRE}" stroke-width="1.6"/>')
        self.t((x1 + x2) / 2, y - 2, l1, 11.5, "middle", WIRE, 700)
        self.t((x1 + x2) / 2, y + 11, l2, 10.5, "middle", WIRE)

    # ---------- frame ----------
    def svg(self, total):
        tb_x, tb_y, tb_w, tb_h = W - 24 - 560, H - 24 - 118, 560, 118
        frame = [
            f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
            f'<rect x="24" y="24" width="{W - 48}" height="{H - 48}" fill="none" stroke="{INK}" stroke-width="1.6"/>',
            f'<text x="44" y="66" font-size="26" font-weight="800" fill="{INK}" font-family="{SANS}">{escape(self.title)}</text>',
            f'<text x="44" y="91" font-size="14.5" fill="{MUTED}" font-family="{SANS}">{escape(self.subtitle)}</text>',
            f'<rect x="{tb_x}" y="{tb_y}" width="{tb_w}" height="{tb_h}" fill="#fff" stroke="{INK}" stroke-width="1.6"/>',
            f'<line x1="{tb_x}" y1="{tb_y + 46}" x2="{tb_x + tb_w}" y2="{tb_y + 46}" stroke="{INK}" stroke-width="1"/>',
            f'<line x1="{tb_x}" y1="{tb_y + 82}" x2="{tb_x + tb_w}" y2="{tb_y + 82}" stroke="{INK}" stroke-width="1"/>',
            f'<line x1="{tb_x + 380}" y1="{tb_y + 46}" x2="{tb_x + 380}" y2="{tb_y + tb_h}" stroke="{INK}" stroke-width="1"/>',
            f'<text x="{tb_x + 14}" y="{tb_y + 31}" font-size="20" font-weight="800" fill="{INK}" font-family="{SANS}">ResQBot Mini · Electrical schematic</text>',
            f'<text x="{tb_x + 14}" y="{tb_y + 70}" font-size="15" font-weight="600" fill="{INK}" font-family="{SANS}">{escape(self.title)}</text>',
            f'<text x="{tb_x + 14}" y="{tb_y + 106}" font-size="12.5" fill="{MUTED}" font-family="{SANS}">Drawn: {BY} · Date: {DATE} · Resistors ¼ W 5 %</text>',
            f'<text x="{tb_x + 394}" y="{tb_y + 70}" font-size="15" font-weight="700" fill="{INK}" font-family="{SANS}">Sheet {self.num} of {total}</text>',
            f'<text x="{tb_x + 394}" y="{tb_y + 106}" font-size="13" fill="{MUTED}" font-family="{SANS}">Rev {REV}</text>',
        ]
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
                + "".join(frame) + "".join(self.p) + "</svg>")


# ================= Arduino Uno pin table =================
# (key, label, net); net None = not used
U_LEFT = [("IOREF", "IOREF", None), ("RESET", "RESET", None), ("3V3", "3.3V", None), ("5V", "5V", "+5V"),
          ("GND1", "GND", "GND"), ("GND2", "GND", "GND"), ("VIN", "VIN", None), ("A0", "A0", "MQ2_AO"),
          ("A1", "A1", "VBAT_SENSE"), ("A2", "A2", "US_TRIG"), ("A3", "A3", "US_ECHO"), ("A4", "A4/SDA", "I2C_SDA"),
          ("A5", "A5/SCL", "I2C_SCL")]
U_RIGHT = [("D0", "D0/RX", "LINK_RX"), ("D1", "D1/TX", "LINK_TX_5V"), ("D2", "D2", "DHT_DATA"), ("D3", "D3~", "BUZZER_DRV"),
           ("D4", "D4", "PIR_OUT"), ("D5", "D5~", "MOT_ENA"), ("D6", "D6~", "MOT_ENB"), ("D7", "D7", "MOT_IN1"),
           ("D8", "D8", "MOT_IN2"), ("D9", "D9~", "MOT_IN3"), ("D10", "D10~", "MOT_IN4"), ("D11", "D11~", "SERVO_PAN"),
           ("D12", "D12", "SERVO_TILT"), ("D13", "D13", "BEACON_DRV"), ("GND3", "GND", "GND"), ("AREF", "AREF", None)]
NOTE = {"A0": "analog in", "A1": "analog in", "A2": "digital out", "A3": "digital in", "A4": "I²C data", "A5": "I²C clock",
        "D0": "serial from CAM", "D1": "serial to CAM", "D2": "1-wire data", "D3": "out", "D4": "digital in",
        "D5": "PWM", "D6": "PWM", "D7": "out", "D8": "out", "D9": "out", "D10": "out", "D11": "servo", "D12": "servo",
        "D13": "out (+ on-board LED)", "VIN": "not used: +5V feeds the 5V pin", "IOREF": "", "RESET": "", "3V3": "",
        "AREF": "", "5V": "", "GND1": "", "GND2": "", "GND3": ""}


def uno(s, x, w, top, pitch):
    py = lambda i: top + 72 + i * pitch
    rows = max(len(U_LEFT), len(U_RIGHT))
    bottom = py(rows - 1) + 30
    s.add(f'<rect x="{x}" y="{top}" width="{w}" height="{bottom - top}" rx="8" fill="#eef6ff" stroke="{INK}" stroke-width="2.4"/>')
    s.t(x + w / 2, top + 26, "U1 · Arduino Uno R3", 16, "middle", weight=800)
    s.t(x + w / 2, top + 45, "ATmega328P · 5 V logic", 12.5, "middle", color=MUTED)
    pins = {}
    for side, table in (("L", U_LEFT), ("R", U_RIGHT)):
        for i, (key, label, net) in enumerate(table):
            y = py(i)
            if side == "L":
                s.line(x - 30, y, x, y); s.t(x + 8, y + 5, label, 13, mono=True); end = (x - 30, y)
            else:
                s.line(x + w, y, x + w + 30, y); s.t(x + w - 8, y + 5, label, 13, "end", mono=True); end = (x + w + 30, y)
            pins[key] = (end, net)
            if net is None:
                s.nc(*end)
    s.t(x + w / 2, bottom - 12, "USB-B · power jack unused", 11, "middle", color=MUTED)
    return pins, bottom, py


# ================= Sheet 1: system overview =================
def sheet_overview():
    s = Sheet(1, "System overview: every module connected",
              "Arduino Uno reads all sensors and drives the robot; the ESP32-CAM streams video and serves the dashboard.")
    pins, bottom, r = uno(s, 700, 280, 140, 46)
    P = lambda k: pins[k][0]

    # ---- left: analog side ----
    x, y = P("5V"); s.wire((x, y), (640, y)); s.flag(640, y, "+5V", "left")
    for k in ("GND1", "GND2"):
        x, y = P(k); s.wire((x, y), (640, y)); s.flag(640, y, "GND", "left")
    x, y = P("A0"); s.wire((x, y), (430, y))
    s.module(150, 250, "U6 · MQ-2 (AO) · +5V · GND", "", right=[("AO", "", y)], top=y - 17, bottom=y + 17)
    x, y = P("A1"); s.wire((x, y), (600, y)); s.block(480, 600, y, "R3 10k / R4 10k", "+ C3, battery sense"); s.wire((480, y), (470, y)); s.flag(470, y, "VBAT", "left")
    ya, yb = P("A2")[1], P("A3")[1]
    for k in ("A2", "A3"):
        x, y = P(k); s.wire((x, y), (430, y))
    s.module(210, 190, "U4 · HC-SR04", "+5V · GND", right=[("T", "TRIG", ya), ("E", "ECHO", yb)], top=ya - 22, bottom=yb + 19, title_inside=True)
    ya, yb = P("A4")[1], P("A5")[1]
    for k in ("A4", "A5"):
        x, y = P(k); s.wire((x, y), (430, y))
    s.module(210, 190, "U3 · MLX90614", "GY-906 · +5V · 0x5A", right=[("D", "SDA", ya), ("C", "SCL", yb)], top=ya - 19, bottom=yb + 22, title_inside=True)
    s.t(56, P("VIN")[1] + 5, "VIN unused: the 5 V rail feeds the Uno's 5V pin", 12, color=MUTED)

    # ---- right: digital side ----
    y0, y1 = P("D0")[1], P("D1")[1]
    x, y = P("D0"); s.wire((x, y), (1120, y))
    x, y = P("D1"); s.wire((x, y), (1030, y)); s.block(1030, 1110, y, "R1 1k / R2 2k", "5 V → 3.3 V"); s.wire((1110, y), (1120, y))
    s.module(1150, 230, "U2 · ESP32-CAM", "camera · Wi-Fi AP · dashboard", left=[("TX", "IO14 TX", y0), ("RX", "IO13 RX", y1)],
             top=y0 - 24, bottom=y1 + 20, title_inside=True)
    x, y = P("D2"); s.wire((x, y), (1150, y))
    s.module(1180, 270, "U9 · DHT11 (DATA) · +5V · GND", "", left=[("D", "", y)], top=y - 17, bottom=y + 17)
    x, y = P("D3"); s.wire((x, y), (1030, y)); s.block(1030, 1150, y, "R5 · Q1 BC547 · D1", "buzzer driver"); s.wire((1150, y), (1180, y))
    s.module(1210, 200, "BZ1 · 5 V buzzer (−)", "", left=[("B", "", y)], top=y - 17, bottom=y + 17)
    x, y = P("D4"); s.wire((x, y), (1150, y))
    s.module(1180, 270, "U5 · PIR HC-SR501 (OUT) · +5V", "", left=[("O", "", y)], top=y - 17, bottom=y + 17)
    lp = []
    for k, lab in (("D5", "ENA"), ("D6", "ENB"), ("D7", "IN1"), ("D8", "IN2"), ("D9", "IN3"), ("D10", "IN4")):
        x, y = P(k); s.wire((x, y), (1090, y)); lp.append((lab, lab, y))
    outs = [("O1", "OUT1", r(5)), ("O2", "OUT2", r(7)), ("O3", "OUT3", r(8)), ("O4", "OUT4", r(10))]
    mp = s.module(1120, 230, "U7 · L298N", "+12V ← VBAT · GND", left=lp, right=outs, top=r(5) - 21, bottom=r(10) + 22, title_inside=True)
    for a, b, first in (("O1", "O2", 1), ("O3", "O4", 3)):
        (xa, ya), (xb, yb) = mp[a], mp[b]
        s.wire((xa, ya), (1520, ya)); s.wire((xb, yb), (1520, yb))
        for k, mx in enumerate((1420, 1520)):
            s.motor(mx, ya, f"M{first + k}", pitch=yb - ya)
            if k == 0:
                s.dot(mx, ya); s.dot(mx, yb)
    s.t(1470, r(5) - 10, "left pair", 11.5, "middle", MUTED); s.t(1470, r(8) - 10, "right pair", 11.5, "middle", MUTED)
    for k, ref in (("D11", "SV2 · SG90 pan (SIG)"), ("D12", "SV1 · SG90 tilt (SIG)")):
        x, y = P(k); s.wire((x, y), (1090, y))
        s.module(1120, 230, ref + " · +5V · GND", "", left=[("S", "", y)], top=y - 17, bottom=y + 17)
    x, y = P("D13"); s.wire((x, y), (1030, y)); s.block(1030, 1150, y, "R6 · Q2 · R7", "beacon driver"); s.wire((1150, y), (1180, y))
    s.module(1210, 230, "LED1 · beacon (K), from +5V", "", left=[("K", "", y)], top=y - 17, bottom=y + 17)
    x, y = P("GND3"); s.wire((x, y), (1040, y)); s.flag(1040, y, "GND", "right")

    # ---- power chain ----
    s.panel(40, 960, 680, 112, "Power (sheet 2)")
    chain = [("BT1", "7.4 V 2S pack"), ("J1 · F1 3 A", "DC jack · fuse"), ("SW1", "power switch"), ("VBAT", "U7 L298N +12V"),
             ("U8 LM2596", "→ +5V rail"), ("+5V", "Uno, CAM, sensors")]
    for i, (a, b) in enumerate(chain):
        bx = 56 + i * 110
        s.add(f'<rect x="{bx}" y="1000" width="100" height="52" rx="6" fill="#fff" stroke="{PWR}" stroke-width="1.6"/>')
        s.t(bx + 50, 1021, a, 12.5, "middle", PWR, 700); s.t(bx + 50, 1040, b, 10.5, "middle", MUTED)
        if i < len(chain) - 1:
            s.line(bx + 100, 1026, bx + 110, 1026, PWR, 2)
    s.t(740, 990, "Phone ⇄ Wi-Fi ResQBot-01 ⇄ U2 ESP32-CAM ⇄ serial 115200 ⇄ U1 Uno ⇄ sensors and motors", 13, color=WIRE, weight=600)
    s.t(740, 1012, "Net flags with the same name are connected. GND is common to every module.", 12.5, color=MUTED)
    return s


# ================= Sheet 2: power =================
def sheet_power():
    s = Sheet(2, "Power supply", "Battery, protection, motor supply (VBAT) and the single 5 V rail for the Uno, the ESP32-CAM and the sensors.")
    s.battery(140, 250, "BT1", ["7.4 V 2S Li-ion", "2500 mAh, BMS"])
    j = s.module(230, 120, "J1", "DC jack", left=[("p", "+", 200), ("n", "−", 240)], right=[("P", "+", 200), ("N", "−", 240)], top=150, bottom=262)
    s.wire((140, 250), (140, 200), j["p"])
    s.wire((140, 350), (140, 380), (180, 380), (180, 240), j["n"])
    s.wire(j["N"], (410, 240)); s.gnd(410, 240)
    s.wire(j["P"], (420, 200)); s.fuse(420, 200, "F1", "3 A")
    s.wire((500, 200), (530, 200)); s.switch(530, 200, "SW1", "rocker")
    s.wire((610, 200), (760, 200)); s.dot(680, 200)
    u7 = s.module(790, 210, "U7 · L298N", "motor driver module",
                  left=[("V", "+12V", 200), ("G", "GND", 240), ("5", "+5V", 280)],
                  right=[("O1", "OUT1", 200), ("O2", "OUT2", 240), ("O3", "OUT3", 280), ("O4", "OUT4", 320)], top=134, bottom=346)
    s.wire(u7["G"], (730, 240)); s.gnd(730, 240); s.nc(*u7["5"])
    for k, net in (("O1", "MOT_L+"), ("O2", "MOT_L−"), ("O3", "MOT_R+"), ("O4", "MOT_R−")):
        s.flag(*u7[k], net, "right")
    s.lines(790, 376, ["ENA/ENB jumpers removed: speed comes from the Uno (sheet 5).",
                       "5V-EN jumper ON; the module's +5V pin is not used."], 12.5, 18, MUTED)
    s.wire((680, 200), (680, 470), (760, 470)); s.dot(680, 330); s.wire((680, 330), (620, 330)); s.flag(620, 330, "VBAT", "left")
    u8 = s.module(790, 210, "U8 · LM2596", "buck converter, set 5.0 V",
                  left=[("I", "IN+", 470), ("IG", "IN−", 510)], right=[("O", "OUT+", 470), ("OG", "OUT−", 510)], top=418, bottom=530)
    s.wire(u8["IG"], (735, 510)); s.gnd(735, 510)
    s.wire(u8["OG"], (1050, 510)); s.gnd(1050, 510)
    s.wire(u8["O"], (1300, 470)); s.dot(1110, 470); s.dot(1240, 470)
    s.cap(1110, 470, "C1", "470 µF 10 V", polar=True); s.gnd(1110, 530)
    s.cap(1240, 470, "C2", "100 nF"); s.gnd(1240, 530)
    s.pwr(1300, 470, "+5V")
    s.panel(1340, 410, 300, 300, "+5V loads (peak)")
    s.lines(1356, 466, ["U1 Arduino Uno         50 mA", "U2 ESP32-CAM + flash  310+ mA", "SV1, SV2 servos  2 x 650 mA",
                        "U6 MQ-2 heater        150 mA", "U4 HC-SR04             15 mA", "U3, U5, U9 sensors      6 mA",
                        "BZ1 + LED1             50 mA", "Total ≈ 1.9 A peak", "LM2596 module: 3 A max ✓"], 12, 22, mono=True)
    s.panel(40, 600, 760, 230, "Arduino Uno supply")
    u1 = s.module(300, 270, "U1 · Arduino Uno", "fed on the 5V pin (regulator bypassed)",
                  left=[("5V", "5V", 700), ("G", "GND", 740)], right=[("VIN", "VIN", 700)], top=650, bottom=780)
    s.wire(u1["5V"], (210, 700)); s.pwr(210, 700, "+5V")
    s.wire(u1["G"], (240, 740)); s.gnd(240, 740)
    s.nc(*u1["VIN"])
    s.lines(640, 700, ["VIN not used.", "No 3.3 V rail is needed:", "every sensor runs on 5 V."], 12.5, 19, MUTED)
    s.panel(40, 860, 1000, 180, "Notes")
    s.lines(56, 912, ["1. Turn the LM2596 screw until OUT+ reads 5.0 V on a multimeter BEFORE connecting the Uno or any sensor.",
                      "2. F1 (3 A glass or blade fuse) goes in the + lead, close to the battery. The pack's BMS is a second layer.",
                      "3. Join all GNDs at one point near the L298N (star ground) so motor current does not upset the sensors.",
                      "4. Uploading to the Uno over USB: switch SW1 off and unplug the D0 wire (the ESP32-CAM link) first.",
                      "5. The L298N drops ~2 V: motors see ~5.5–6 V from the 7.4 V pack, which suits 6 V BO motors."], 13, 23)
    return s


# ================= Sheet 3: controller =================
def sheet_controller():
    s = Sheet(3, "Controller U1: Arduino Uno pin assignment", "Every Uno pin with its net. Matches firmware/ResQBot_Uno/config.h.")
    pins, bottom, r = uno(s, 680, 320, 120, 44)
    for key, ((x, y), net) in pins.items():
        side = "L" if key in [p[0] for p in U_LEFT] else "R"
        note = NOTE.get(key, "")
        if net is None:
            if note:
                s.t(x - 14 if side == "L" else x + 14, y + 5, note, 12, "end" if side == "L" else "start", MUTED)
            continue
        if net == "+5V":
            s.wire((x, y), (x - 110, y)); s.pwr(x - 110, y, net); continue
        if net == "GND":
            s.wire((x, y), (x - 40 if side == "L" else x + 40, y)); s.gnd(x - 40 if side == "L" else x + 40, y); continue
        s.flag(x, y, net, "left" if side == "L" else "right")
        tw = len(net) * 7.4 + 30
        if note:
            s.t(x - tw - 10 if side == "L" else x + tw + 10, y + 5, note, 12, "end" if side == "L" else "start", MUTED)
    s.panel(40, 900, 1030, 140, "Design rules for U1")
    s.lines(56, 948, ["• Everything is 5 V logic: HC-SR04, PIR, MQ-2, DHT11 and MLX90614 connect directly. Only D1 → ESP32-CAM is divided.",
                      "• Servo library uses Timer1 (no PWM on D9/D10): those pins only carry IN3/IN4 direction signals. Speed PWM is on D5/D6.",
                      "• D0/D1 are shared with USB: unplug the D0 wire while uploading."], 13, 23)
    return s


# ================= Sheet 4: sensors =================
def sheet_sensors():
    s = Sheet(4, "Sensor interfaces", "All sensors run on the 5 V rail and connect straight to the Uno (no level shifting).")
    s.panel(40, 110, 520, 400, "Thermal · U3 MLX90614 (GY-906)")
    u = s.module(300, 190, "U3", "GY-906 module", left=[("V", "VIN", 220), ("G", "GND", 260), ("C", "SCL", 300), ("D", "SDA", 340)], top=170, bottom=360)
    s.wire(u["V"], (130, 220)); s.pwr(130, 220, "+5V")
    s.wire(u["G"], (180, 260)); s.gnd(180, 260)
    s.flag(*u["C"], "I2C_SCL", "left"); s.flag(*u["D"], "I2C_SDA", "left")
    s.lines(56, 396, ["SCL → A5, SDA → A4. The module has its own 3.3 V regulator", "and 10 kΩ pull-ups. I²C address 0x5A, 100 kHz.",
                      "Fit a black tube, 10 mm inside × 22 mm long, over the", "sensor to narrow its view to ~25°."], 12.5, 19, MUTED)
    s.panel(580, 110, 520, 400, "Distance · U4 HC-SR04")
    u = s.module(920, 160, "U4", "HC-SR04", left=[("V", "VCC", 220), ("T", "TRIG", 260), ("E", "ECHO", 300), ("G", "GND", 340)], top=170, bottom=360)
    s.wire(u["V"], (850, 220)); s.pwr(850, 220, "+5V")
    s.flag(*u["T"], "US_TRIG", "left"); s.flag(*u["E"], "US_ECHO", "left")
    s.wire(u["G"], (875, 340)); s.gnd(875, 340)
    s.lines(596, 434, ["TRIG → A2, ECHO → A3, both 5 V: no divider needed on the Uno.", "Range 2–400 cm; read every 60 ms."], 12.5, 19, MUTED)
    s.panel(1120, 110, 520, 400, "Motion · U5 HC-SR501 PIR")
    u = s.module(1440, 160, "U5", "HC-SR501", left=[("V", "VCC", 220), ("O", "OUT", 260), ("G", "GND", 300)], top=170, bottom=320)
    s.wire(u["V"], (1340, 220)); s.pwr(1340, 220, "+5V")
    s.flag(*u["O"], "PIR_OUT", "left")
    s.wire(u["G"], (1380, 300)); s.gnd(1380, 300)
    s.lines(1136, 396, ["OUT → D4 (3.3 V high, read fine by the Uno).", "Jumper on H (repeat trigger), time knob minimum,",
                        "sensitivity mid. Needs ~30 s to settle after power-on."], 12.5, 19, MUTED)
    s.panel(40, 540, 520, 420, "Smoke / gas · U6 MQ-2")
    u = s.module(80, 170, "U6", "MQ-2 module", right=[("V", "VCC", 630), ("G", "GND", 670), ("D", "DO", 710), ("A", "AO", 750)], top=585, bottom=780)
    s.wire(u["V"], (320, 630)); s.pwr(320, 630, "+5V")
    s.wire(u["G"], (300, 670)); s.gnd(300, 670); s.nc(*u["D"])
    s.flag(*u["A"], "MQ2_AO", "right")
    s.lines(56, 860, ["AO → A0 directly (0–5 V = 0–1023).", "Heater 150 mA, 2–3 min warm-up.", "Set GAS_ALARM_RAW ≈ clean-air reading + 40 %."], 12.5, 19, MUTED)
    s.panel(580, 540, 520, 420, "Air temperature + humidity · U9 DHT11")
    u = s.module(900, 180, "U9", "DHT11 module", left=[("V", "VCC", 610), ("D", "DATA", 690), ("G", "GND", 730)], top=548, bottom=760)
    s.wire(u["V"], (720, 610)); s.pwr(720, 610, "+5V"); s.dot(780, 610)
    s.res(780, 610, "R8", "10 kΩ")
    s.wire(u["D"], (700, 690)); s.dot(780, 690)
    s.flag(700, 690, "DHT_DATA", "left")
    s.wire(u["G"], (850, 730)); s.gnd(850, 730)
    s.lines(596, 820, ["DATA → D2. R8 is already on the 3-pin module;", "fit it only for a bare 4-pin DHT11.",
                       "0–50 °C ±2 °C, 20–90 % RH; read every 5 s.", "Gives the air temperature next to the IR readings."], 12.5, 19, MUTED)
    s.panel(1120, 540, 520, 420, "Battery voltage · divider to A1")
    s.flag(1240, 620, "VBAT", "left"); s.wire((1240, 620), (1300, 620))
    s.res(1300, 620, "R3", "10 kΩ"); s.dot(1300, 700)
    s.wire((1300, 700), (1500, 700)); s.flag(1500, 700, "VBAT_SENSE", "right"); s.dot(1400, 700)
    s.res(1300, 700, "R4", "10 kΩ"); s.gnd(1300, 780)
    s.cap(1400, 700, "C3", "100 nF"); s.gnd(1400, 760)
    s.lines(1136, 860, ["8.4 V full → 4.2 V · 6.8 V low → 3.4 V at A1.", "C3 filters motor noise. Calibrate BATTERY_ADC_CAL."], 12.5, 19, MUTED)
    return s


# ================= Sheet 5: drive and thermal head =================
def sheet_drive():
    s = Sheet(5, "Motor drive and thermal head", "L298N with four BO motors (two parallel pairs) and the two pan-tilt servos.")
    s.panel(40, 110, 1060, 640, "Drive · U7 L298N")
    u = s.module(520, 230, "U7 · L298N", "dual H-bridge module",
                 left=[("O1", "OUT1", 300), ("O2", "OUT2", 380), ("O3", "OUT3", 520), ("O4", "OUT4", 600)],
                 right=[("ENA", "ENA", 300), ("IN1", "IN1", 340), ("IN2", "IN2", 380), ("IN3", "IN3", 440), ("IN4", "IN4", 480),
                        ("ENB", "ENB", 520), ("V", "+12V", 580), ("G", "GND", 620)], top=230, bottom=650)
    for k, pin in (("ENA", "D5"), ("IN1", "D7"), ("IN2", "D8"), ("IN3", "D9"), ("IN4", "D10"), ("ENB", "D6")):
        s.flag(*u[k], "MOT_" + k, "right")
        s.t(u[k][0] + 100, u[k][1] + 5, "← Uno " + pin, 12, color=MUTED)
    s.wire(u["V"], (820, 580)); s.flag(820, 580, "VBAT", "right")
    s.wire(u["G"], (800, 620)); s.gnd(800, 620)
    for a, b, refs in (("O1", "O2", ("M1", "M2")), ("O3", "O4", ("M3", "M4"))):
        (xa, ya), (xb, yb) = u[a], u[b]
        s.wire((xa, ya), (120, ya)); s.wire((xb, yb), (120, yb))
        for x, ref in ((380, refs[0]), (270, refs[1])):
            s.motor(x, ya, ref, pitch=yb - ya); s.dot(x, ya); s.dot(x, yb)
        s.cap(120, ya, "C4" if a == "O1" else "C5", "100 nF", pitch=yb - ya)
    s.t(330, 285, "LEFT pair (MOT_L±)", 12.5, "middle", MUTED); s.t(330, 505, "RIGHT pair (MOT_R±)", 12.5, "middle", MUTED)
    s.lines(56, 690, ["Motors of a pair are wired in parallel with the same polarity; swap a pair's two wires if that side runs backwards.",
                      "Remove the ENA/ENB jumpers. ENx = PWM speed (D5/D6, ~980 Hz), INx = direction. Each channel handles 2 A."], 12.5, 20, MUTED)
    s.panel(40, 780, 1060, 240, "Drive logic (firmware ResQBot_Uno)")
    rows = [("Action", "IN1", "IN2", "IN3", "IN4", "ENA / ENB"), ("Forward", "H", "L", "H", "L", "PWM / PWM"),
            ("Backward", "L", "H", "L", "H", "PWM / PWM"), ("Spin left", "L", "H", "H", "L", "PWM / PWM"),
            ("Spin right", "H", "L", "L", "H", "PWM / PWM"), ("Stop", "L", "L", "L", "L", "0 / 0")]
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            s.t(60 + [0, 200, 290, 380, 470, 580][j], 838 + i * 30, cell, 13, weight=700 if i == 0 else 400, mono=j > 0 and i > 0)
    s.lines(760, 838, ["PWM 8-bit (0–255).", "Search speed 170, crawl 130,", "turn 180 (config.h).",
                       "Dead-man: stop after 600 ms", "without a phone command."], 12.5, 22, MUTED)
    s.panel(1120, 110, 520, 640, "Thermal head · SV1, SV2 (SG90)")
    for y, ref, net, note in ((240, "SV1", "SERVO_TILT", "tilt on D12: 70° floor / 95° level"), (460, "SV2", "SERVO_PAN", "pan on D11: 20°–160°, 10° steps")):
        u = s.module(1420, 180, ref, "SG90 micro servo", left=[("S", "SIG", y), ("V", "V+", y + 40), ("G", "GND", y + 80)], top=y - 52, bottom=y + 104)
        s.flag(*u["S"], net, "left")
        s.wire(u["V"], (1250, y + 40)); s.pwr(1250, y + 40, "+5V")
        s.wire(u["G"], (1340, y + 80)); s.gnd(1340, y + 80)
        s.t(1136, y + 134, f"{ref} {note}", 12.5, color=MUTED)
    s.lines(1136, 670, ["Wires: orange = SIG, red = V+, brown = GND.", "Servo current spikes are buffered by C1 470 µF",
                        "on the +5V rail (sheet 2)."], 12.5, 19, MUTED)
    return s


# ================= Sheet 6: alerts and camera link =================
def sheet_alerts():
    s = Sheet(6, "Alerts and the ESP32-CAM link", "Buzzer and beacon drivers, and the serial link that carries all sensor data to the camera board.")
    s.panel(40, 110, 520, 560, "Buzzer driver · Q1 (D3)")
    s.pwr(300, 200, "+5V"); s.wire((300, 200), (300, 210)); s.wire((300, 210), (380, 210)); s.dot(300, 210)
    s.buzzer(300, 210, "BZ1", "5 V active")
    s.diode(380, 210, "D1", "1N4148", pitch=80, cathode_top=True)
    s.wire((300, 290), (380, 290)); s.dot(300, 290)
    q = s.npn(286, 370, "Q1", "BC547")
    s.wire((300, 290), q["C"]); s.gnd(*q["E"])
    s.wire(q["B"], (230, 370)); s.res(150, 370, "R5", "1 kΩ", "h"); s.flag(150, 370, "BUZZER_DRV", "left")
    s.lines(56, 520, ["D3 high → Q1 on → buzzer sounds (~30 mA).", "D1 absorbs the coil's turn-off spike.",
                      "Base current ≈ (5 − 0.7) V / 1 kΩ = 4.3 mA."], 12.5, 19, MUTED)
    s.panel(580, 110, 520, 560, "Beacon driver · Q2 (D13)")
    s.pwr(840, 200, "+5V"); s.wire((840, 200), (840, 210))
    s.res(840, 210, "R7", "100 Ω")
    s.led(840, 290, "LED1", "white, bright")
    q = s.npn(826, 410, "Q2", "BC547")
    s.wire((840, 350), q["C"]); s.gnd(*q["E"])
    s.wire(q["B"], (770, 410)); s.res(690, 410, "R6", "1 kΩ", "h"); s.flag(690, 410, "BEACON_DRV", "left")
    s.lines(596, 540, ["D13 high → Q2 on → LED lit from +5V.", "I ≈ (5 − 3.1 − 0.1) V / 100 Ω ≈ 18 mA (white).",
                       "Use 150 Ω for a red LED.", "Flashes 8 times a second during a survivor alert."], 12.5, 19, MUTED)
    s.panel(1120, 110, 520, 560, "Camera + Wi-Fi · U2 ESP32-CAM")
    u = s.module(1420, 180, "U2", "ESP32-CAM AI-Thinker", left=[("V", "5V", 230), ("G", "GND", 270), ("RX", "IO13", 330), ("TX", "IO14", 390)],
                 top=180, bottom=430)
    s.wire(u["V"], (1200, 230)); s.pwr(1200, 230, "+5V"); s.dot(1250, 230)
    s.cap(1250, 230, "C6", "220 µF 10 V", polar=True); s.gnd(1250, 290)
    s.gnd(*u["G"])
    s.wire(u["RX"], (1340, 330)); s.dot(1340, 330)
    s.res(1260, 330, "R1", "1 kΩ", "h")
    s.res(1340, 330, "R2", "2 kΩ"); s.gnd(1340, 410)
    s.flag(1260, 330, "LINK_TX_5V", "left")
    s.wire(u["TX"], (1378, 390), (1378, 470), (1260, 470)); s.flag(1260, 470, "LINK_RX", "left")
    s.lines(1136, 512, ["LINK_TX_5V = Uno D1 (5 V) → R1/R2 → 3.3 V at IO13.", "LINK_RX = IO14 (3.3 V) → Uno D0 directly.",
                        "115200 baud: status every 0.4 s, commands back.", "Leave the micro-SD slot empty (IO13/14 are SD pins).",
                        "C6 stops resets when the flash LED (IO4) turns on."], 12.5, 21, MUTED)
    s.panel(40, 700, 1600, 320, "Module header pin order (as printed on the boards)")
    hdr = [("U3 MLX90614 GY-906", "VIN · GND · SCL · SDA"), ("U4 HC-SR04", "VCC · TRIG · ECHO · GND"),
           ("U5 HC-SR501", "VCC · OUT · GND (check under the dome)"), ("U6 MQ-2 module", "VCC · GND · DO · AO"),
           ("U9 DHT11 module", "VCC · DATA · GND  (bare: VCC DATA nc GND)"), ("SV1, SV2 SG90", "brown GND · red V+ · orange SIG"),
           ("U7 L298N logic header", "ENA · IN1 · IN2 · IN3 · IN4 · ENB"), ("U8 LM2596", "IN+ · IN−  |  OUT+ · OUT−"),
           ("U2 ESP32-CAM, side 1", "5V · GND · IO12 · IO13 · IO15 · IO14 · IO2 · IO4"), ("U2 ESP32-CAM, side 2", "3V3 · IO16 · IO0 · GND · VCC · U0R · U0T · GND"),
           ("LED1 Piranha", "2 anode pins (+), 2 cathode pins (−, notched corner)"), ("Q1, Q2 BC547", "flat face toward you: C · B · E")]
    for i, (a, b) in enumerate(hdr):
        col, row = divmod(i, 6)
        x0, y0 = 60 + col * 800, 760 + row * 40
        s.t(x0, y0, a, 13.5, weight=700); s.t(x0 + 250, y0, b, 13.5, mono=True)
    return s


# ================= netlist and parts =================
NETS = [
    ("BAT+", "BT1.+, J1.+"), ("BAT_FUSED", "J1.+ out, F1.1"), ("SW_IN", "F1.2, SW1.1"),
    ("VBAT", "SW1.2, U7.+12V, U8.IN+, R3.1"),
    ("+5V", "U8.OUT+, C1.+, C2.1, U1.5V, U2.5V, C6.+, U3.VIN, U4.VCC, U5.VCC, U6.VCC, U9.VCC, R8.1, SV1.V+, SV2.V+, BZ1.+, D1.K, R7.1"),
    ("GND", "BT1.−, J1.−, U7.GND, U8.IN−, U8.OUT−, U1.GND ×3, U2.GND, U3.GND, U4.GND, U5.GND, U6.GND, U9.GND, SV1.GND, SV2.GND, "
            "R2.2, R4.2, C1.−, C2.2, C3.2, C6.−, Q1.E, Q2.E"),
    ("LINK_TX_5V", "U1.D1, R1.1"), ("LINK_TX_3V3", "R1.2, R2.1, U2.IO13"), ("LINK_RX", "U2.IO14, U1.D0"),
    ("I2C_SDA", "U1.A4, U3.SDA"), ("I2C_SCL", "U1.A5, U3.SCL"),
    ("US_TRIG", "U1.A2, U4.TRIG"), ("US_ECHO", "U4.ECHO, U1.A3"), ("PIR_OUT", "U5.OUT, U1.D4"),
    ("MQ2_AO", "U6.AO, U1.A0"), ("VBAT_SENSE", "R3.2, R4.1, C3.1, U1.A1"), ("DHT_DATA", "U9.DATA, R8.2, U1.D2"),
    ("MOT_ENA", "U1.D5, U7.ENA"), ("MOT_ENB", "U1.D6, U7.ENB"), ("MOT_IN1", "U1.D7, U7.IN1"), ("MOT_IN2", "U1.D8, U7.IN2"),
    ("MOT_IN3", "U1.D9, U7.IN3"), ("MOT_IN4", "U1.D10, U7.IN4"),
    ("MOT_L+", "U7.OUT1, M1.1, M2.1, C4.1"), ("MOT_L−", "U7.OUT2, M1.2, M2.2, C4.2"),
    ("MOT_R+", "U7.OUT3, M3.1, M4.1, C5.1"), ("MOT_R−", "U7.OUT4, M3.2, M4.2, C5.2"),
    ("SERVO_PAN", "U1.D11, SV2.SIG"), ("SERVO_TILT", "U1.D12, SV1.SIG"),
    ("BUZZER_DRV", "U1.D3, R5.1"), ("Q1_BASE", "R5.2, Q1.B"), ("BZ_LOW", "BZ1.−, D1.A, Q1.C"),
    ("BEACON_DRV", "U1.D13, R6.1"), ("Q2_BASE", "R6.2, Q2.B"), ("LED_A", "R7.2, LED1.A"), ("LED_K", "LED1.K, Q2.C"),
]
PARTS = [
    ("U1", "Arduino Uno R3 (you have it)", "", "3"), ("U2", "ESP32-CAM AI-Thinker + OV2640 (you have it)", "", "6"),
    ("U3", "MLX90614 IR thermometer, GY-906 module", "0x5A", "4"), ("U4", "HC-SR04 ultrasonic module", "", "4"),
    ("U5", "HC-SR501 PIR module", "", "4"), ("U6", "MQ-2 gas sensor module", "", "4"),
    ("U7", "L298N dual H-bridge module", "", "2, 5"), ("U8", "LM2596 buck module", "set 5.0 V", "2"),
    ("U9", "DHT11 temperature + humidity module", "", "4"),
    ("BT1", "2S Li-ion pack with BMS and DC jack", "7.4 V 2500 mAh", "2"), ("J1", "5.5 × 2.1 mm DC jack, male, with wire", "", "2"),
    ("F1", "Fuse + inline holder", "3 A", "2"), ("SW1", "Rocker switch SPST", "", "2"),
    ("M1–M4", "BO gear motors (in the chassis kit)", "", "5"), ("SV1, SV2", "SG90 micro servos (tilt, pan)", "", "5"),
    ("R1", "Resistor ¼ W (link divider)", "1 kΩ", "6"), ("R2", "Resistor ¼ W (link divider)", "2 kΩ", "6"),
    ("R3, R4", "Resistor ¼ W (battery divider)", "10 kΩ", "4"), ("R5, R6", "Resistor ¼ W (transistor bases)", "1 kΩ", "6"),
    ("R7", "Resistor ¼ W (LED current)", "100 Ω", "6"), ("R8", "Resistor ¼ W (DHT pull-up, bare sensor only)", "10 kΩ", "4"),
    ("C1", "Electrolytic capacitor", "470 µF 10 V", "2"), ("C2–C5", "Ceramic capacitor", "100 nF", "2–5"),
    ("C6", "Electrolytic capacitor", "220 µF 10 V", "6"), ("Q1, Q2", "NPN transistor", "BC547", "6"),
    ("D1", "Signal diode", "1N4148", "6"), ("BZ1", "Active buzzer", "5 V", "6"), ("LED1", "Bright 5 mm LED (Piranha)", "white", "6"),
]


def netlist_html():
    nets = "".join(f"<tr><td class=m>{escape(n)}</td><td>{escape(c)}</td></tr>" for n, c in NETS)
    parts = "".join(f"<tr><td class=m>{escape(r)}</td><td>{escape(d)}</td><td>{escape(v)}</td><td>{escape(s)}</td></tr>" for r, d, v, s in PARTS)
    return f"""<section class="page doc">
<h2>Netlist</h2>
<p>Every electrical connection, by net name. Pins are written <span class=m>REF.PIN</span>. Check the wiring one net at a time.</p>
<table><tr><th>Net</th><th>Connected pins</th></tr>{nets}</table>
</section>
<section class="page doc">
<h2>Reference designators</h2>
<table><tr><th>Ref</th><th>Part</th><th>Value</th><th>Sheet</th></tr>{parts}</table>
<div class="box"><b>Data path:</b> sensors → U1 Arduino Uno (search logic) → serial 115200 baud (D1 → R1/R2 → IO13, IO14 → D0) →
U2 ESP32-CAM → Wi-Fi hotspot "ResQBot-01" → phone dashboard at http://192.168.4.1, with live video at :81/stream at the same time.
Phone commands travel back the same way.</div>
</section>"""


def main():
    sheets = [sheet_overview(), sheet_power(), sheet_controller(), sheet_sensors(), sheet_drive(), sheet_alerts()]
    total = len(sheets) + 1
    pages = []
    for s in sheets:
        svg = s.svg(total)
        (HERE / f"sheet{s.num}.svg").write_text(svg, encoding="utf-8")
        pages.append(f'<section class="page sheet">{svg}</section>')
    index = "".join(f"<tr><td>{s.num}</td><td>{escape(s.title)}</td></tr>" for s in sheets) + f"<tr><td>{total}</td><td>Netlist and reference designators</td></tr>"
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>ResQBot Mini — Schematics</title>
<style>
@page {{ size: A3 landscape; margin: 0; }}
html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{ margin: 0; font: 15px/1.5 "Segoe UI", Arial, sans-serif; color: #1b1b1b; }}
.page {{ width: 420mm; height: 297mm; box-sizing: border-box; break-after: page; overflow: hidden; }}
.sheet svg {{ width: 420mm; height: 297mm; display: block; }}
.doc {{ padding: 16mm 20mm; }}
h1 {{ font-size: 40px; margin: 0 0 6px; }} h2 {{ font-size: 26px; margin: 0 0 10px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13.5px; }}
th {{ background: #1b1b1b; color: #fff; text-align: left; padding: 6px 10px; }}
td {{ padding: 5px 10px; border-bottom: 1px solid #dde3ea; vertical-align: top; }}
.m {{ font-family: Consolas, monospace; white-space: nowrap; }}
.box {{ margin-top: 16px; padding: 12px 16px; background: #eef6ff; border: 1px solid #b8d4f5; border-radius: 8px; }}
.cover {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14mm; align-items: start; }}
</style></head><body>
<section class="page doc"><div class="cover"><div>
<h1>ResQBot Mini</h1><h2>Electrical schematics · Rev {REV}</h2>
<p><b>Arduino Uno</b> is the main board: it reads every sensor (MLX90614 thermal, DHT11, HC-SR04, PIR, MQ-2, battery) and drives
the motors, servos, buzzer and beacon. <b>ESP32-CAM</b> streams live video, runs the Wi-Fi hotspot and the dashboard, and gets all
sensor data from the Uno over a serial link.</p>
<p>Pin numbers and net names match <span class=m>firmware/ResQBot_Uno/config.h</span> and
<span class=m>firmware/ResQCam_Gateway</span>.</p>
<p><b>How to read:</b> blue lines are wires, a dot is a junction, purple flags with the same name are connected,
red symbols are power rails, ✕ marks an unused pin.</p>
<p>{BY} · {DATE}</p></div>
<div><table><tr><th>Sheet</th><th>Content</th></tr>{index}</table></div></div></section>
{''.join(pages)}
{netlist_html()}
</body></html>"""
    (HERE / "ResQBot_Schematics.html").write_text(html, encoding="utf-8")
    print("sheets:", [s.num for s in sheets])


if __name__ == "__main__":
    main()
