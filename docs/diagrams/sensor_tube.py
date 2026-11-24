"""Draws docs/diagrams/sensor_tube.svg: MLX90614 view-limiting tube (cone and straight) with the view cone and a paper template."""
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
W, H = 1600, 1400
INK, MUTE = "#1d2433", "#5b6475"
MM = 20            # px per mm in the cross-sections
out = []


def a(s):
    out.append(s)


def text(x, y, t, size=15, anchor="start", color=INK, weight=400):
    a(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{color}" font-weight="{weight}" '
      f'font-family="Segoe UI, Arial, sans-serif">{t}</text>')


def arrow(x1, y1, x2, y2, color=INK):
    a(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.8" marker-start="url(#h)" marker-end="url(#h)"/>')


def section(cy, rear_r, front_r, title, sub, deg_text):
    """Side cross-section, looking direction to the right. Radii in px."""
    pcb_x, win_x, front_x = 100, 190, 630
    die_x = 110
    wall = 30
    a(f'<rect x="40" y="{cy - 230}" width="1520" height="460" rx="14" fill="#f8fafc" stroke="#d5dce5"/>')
    text(64, cy - 192, title, 22, weight=800)
    text(64, cy - 168, sub, 14.5, color=MUTE)
    # view cone (drawn first, under the parts)
    slope = front_r / (front_x - die_x)
    far = min(1250, die_x + 195 / slope)          # keep the view cone inside its panel
    dy = (far - die_x) * slope
    a(f'<polygon points="{die_x},{cy} {far},{cy - dy:.1f} {far},{cy + dy:.1f}" fill="#ff6b1a" opacity="0.14"/>')
    a(f'<line x1="{die_x}" y1="{cy}" x2="{far}" y2="{cy - dy:.1f}" stroke="#ff6b1a" stroke-width="2" stroke-dasharray="8 6"/>')
    a(f'<line x1="{die_x}" y1="{cy}" x2="{far}" y2="{cy + dy:.1f}" stroke="#ff6b1a" stroke-width="2" stroke-dasharray="8 6"/>')
    # PCB
    a(f'<rect x="{pcb_x - 30}" y="{cy - 150}" width="30" height="300" fill="#2f8f5b" stroke="{INK}" stroke-width="2"/>')
    text(pcb_x - 15, cy + 178, "GY-906 board", 13, "middle", MUTE)
    # can
    a(f'<rect x="{pcb_x}" y="{cy - 91}" width="{win_x - pcb_x}" height="182" fill="#c9d1de" stroke="{INK}" stroke-width="2"/>')
    a(f'<rect x="{win_x - 5}" y="{cy - 42}" width="5" height="84" fill="#4dabf7" stroke="{INK}" stroke-width="1.5"/>')
    a(f'<rect x="{die_x - 6}" y="{cy - 9}" width="12" height="18" fill="#111"/>')
    a(f'<line x1="{die_x}" y1="{cy}" x2="{win_x}" y2="{cy - (win_x - die_x) * slope:.1f}" stroke="#ff6b1a" stroke-width="2"/>')
    a(f'<line x1="{die_x}" y1="{cy}" x2="{win_x}" y2="{cy + (win_x - die_x) * slope:.1f}" stroke="#ff6b1a" stroke-width="2"/>')
    # tube walls (top and bottom)
    for sgn in (-1, 1):
        r_rear, r_front = rear_r, front_r
        pts = [(pcb_x, cy + sgn * (r_rear + wall)), (win_x, cy + sgn * (r_rear + wall)), (front_x, cy + sgn * (r_front + wall)),
               (front_x, cy + sgn * r_front), (win_x, cy + sgn * r_rear), (pcb_x, cy + sgn * r_rear)]
        a('<polygon points="' + " ".join(f"{x},{y:.1f}" for x, y in pts) + f'" fill="#15181f" stroke="{INK}" stroke-width="1.5"/>')
    # labels
    text(die_x + 14, cy + 28, "chip", 12, "start", MUTE)
    text(146, cy - 66, "metal can", 12, "middle", MUTE)
    text(146, cy - 50, "Ø 9.1 mm", 12, "middle", MUTE)
    text(win_x + 4, cy - 55, "window", 13, "start", "#1c7ed6")
    text(520, cy - front_r - wall - 14, "matte black tube", 14, "middle", INK, 700)
    # dimension: length from window to front
    ly = cy + rear_r + 80 if rear_r >= front_r else cy + front_r + 80
    ly = cy + 150
    arrow(win_x, ly, front_x, ly)
    text((win_x + front_x) / 2, ly + 20, "22 mm from window to front", 14, "middle")
    a(f'<line x1="{win_x}" y1="{ly - 6}" x2="{win_x}" y2="{ly + 6}" stroke="{INK}"/><line x1="{front_x}" y1="{ly - 6}" x2="{front_x}" y2="{ly + 6}" stroke="{INK}"/>')
    # dimension: front opening
    ox = front_x + 36
    arrow(ox, cy - front_r, ox, cy + front_r)
    text(ox + 10, cy + 5, f"opening {2 * front_r / MM:.0f} mm", 15, "start", "#d9480f", 700)
    text(ox + 10, cy + 24, "sets the view angle", 13, "start", MUTE)
    # sensor-end diameter
    text(win_x - 6, cy - rear_r - wall - 10, f"sensor end Ø {2 * rear_r / MM:.1f} mm inside", 13, "start", MUTE)
    # angle text inside the cone
    text(930, cy + 6, deg_text, 24, "middle", "#d9480f", 800)
    text(930, cy + 30, "full view angle", 13, "middle", MUTE)
    text(far - 14, cy + 5, "what the sensor sees", 14, "end", "#d9480f", 600)


a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
a('<defs><marker id="h" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
  f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>')
a(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
text(40, 56, "Black view-limiting tube for the MLX90614 thermal sensor", 30, weight=800)
text(40, 84, "Side view (cross-section). The sensor looks to the right. The smallest opening and its distance from the chip decide the view angle.", 15, color=MUTE)

# cone variant: sensor end 9.6 mm, front opening 8 mm; straight: 10 mm
section(350, 4.8 * MM, 4.0 * MM, "Option 1 · Cone, narrowing toward the front", "Back 9.6 mm, front opening 8 mm, 22 mm long. Narrower view, about 18°.", "≈ 18°")
section(830, 5.0 * MM, 5.0 * MM, "Option 2 · Straight tube (recommended)", "Inside diameter 10 mm all the way, 22 mm long. About 22–25° view.", "≈ 22–25°")

# paper template
ty = 1110
a(f'<rect x="40" y="{ty - 20}" width="1520" height="280" rx="14" fill="#f8fafc" stroke="#d5dce5"/>')
text(64, ty + 12, "Paper tube template (full size scale: 8 px = 1 mm)", 20, weight=800)
S = 8
sx, sy = 120, ty + 46
a(f'<rect x="{sx}" y="{sy}" width="{70 * S}" height="{22 * S}" fill="#2b2f3a" stroke="{INK}" stroke-width="2"/>')
for k in (1, 2):
    xx = sx + round(k * 31.4 * S)
    a(f'<line x1="{xx}" y1="{sy}" x2="{xx}" y2="{sy + 22 * S}" stroke="#9aa3b2" stroke-width="1.5" stroke-dasharray="6 5"/>')
text(sx + 70 * S / 2, sy + 22 * S / 2 + 6, "black card, 70 mm × 22 mm  (colour matte black on both sides)", 15, "middle", "#e8edf4", 600)
arrow(sx, sy + 22 * S + 22, sx + 70 * S, sy + 22 * S + 22)
text(sx + 70 * S / 2, sy + 22 * S + 42, "70 mm: about 2 wraps around a 10 mm pen", 14, "middle")
arrow(sx - 16, sy, sx - 16, sy + 22 * S)
text(sx - 24, sy + 22 * S / 2 + 5, "22 mm", 14, "end")
# cone ring
rx, ry = 840, sy + 90
a(f'<circle cx="{rx}" cy="{ry}" r="{7 * S}" fill="#2b2f3a" stroke="{INK}" stroke-width="2"/>')
a(f'<circle cx="{rx}" cy="{ry}" r="{4 * S}" fill="#ffffff" stroke="{INK}" stroke-width="2"/>')
text(rx, ry + 7 * S + 24, "front ring: Ø 14 mm card, 8 mm hole", 14, "middle")
text(rx, ry + 7 * S + 44, "(only for the cone option)", 13, "middle", MUTE)
# steps
steps = ["1  Colour the card matte black, both sides", "2  Roll it tightly round a 10 mm pen, glue the end", "3  Slide off; it should fit the can with light friction",
         "4  Cone option: glue the 8 mm-hole ring on the front", "5  Slip over the can, glue at the BOARD end only", "Never touch or cover the sensor window"]
for i, s in enumerate(steps):
    text(1030, sy + 14 + i * 30, s, 16, weight=700 if i == 5 else 400, color="#c1121f" if i == 5 else INK)
a("</svg>")
(HERE / "sensor_tube.svg").write_text("\n".join(out), encoding="utf-8")
print("ok")
