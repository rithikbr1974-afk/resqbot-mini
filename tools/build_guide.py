"""Builds the stage presentation guide (HTML, then PDF with tools/build_pdf.ps1).

    python tools/build_guide.py
    powershell -File tools/build_pdf.ps1 docs/presentation/ResQBot_Presentation_Guide.html docs/ResQBot_Presentation_Guide.pdf

The full script comes from the speaker notes in docs/presentation/deck/project/slides/*.html, so the PDF and the
slide deck always say the same thing. Slide pictures come from tools/render_slides.py."""
import html, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECK = ROOT / "docs" / "presentation" / "deck" / "project"
SHOTS = ROOT / "docs" / "presentation" / "slides"
OUT = ROOT / "docs" / "presentation" / "ResQBot_Presentation_Guide.html"

index = json.loads((DECK / "deck.json").read_text(encoding="utf-8"))
order = index["order"]
E = html.escape

TITLES = {
    "cover": "Opening", "golden": "72 hours", "problem": "Why searching is slow", "gap": "The gap",
    "solution": "Meet ResQBot Mini", "mission": "One mission, six steps", "architecture": "Two boards, one team",
    "cost": "What it costs", "sweep": "30-pixel thermal camera", "tube": "The ₹5 tube", "score": "Four clues, one score",
    "unconscious": "Finds the silent", "dashboard": "The rescuer’s view", "demo": "LIVE DEMO", "safety": "Safety by design",
    "impact": "Where it can help", "future": "What’s next", "close": "Send the robot first",
}
SPK = {"1": "#FF6B1A", "2": "#2F6FD6", "3": "#1BAF7A", "4": "#C2255C"}


def notes(sid):
    s = (DECK / "slides" / f"{sid}.html").read_text(encoding="utf-8")
    m = re.search(r"<aside>(.*?)</aside>", s, re.S)
    return html.unescape(m.group(1)).strip() if m else ""


def speaker_of(text):
    m = re.match(r"(?:ALL FOUR[^·]*·\s*)?SPEAKER (\d)\s*·\s*([0-9:]+)–([0-9:]+)", text)
    return (m.group(1), m.group(2), m.group(3)) if m else ("4", "14:30", "15:00")


def fmt_script(text):
    """Speaker notes -> HTML: quotes are spoken lines, [brackets] stage directions, CAPS: labels."""
    out = []
    lines = text.split("\n")
    first = lines[0]
    rest = "\n".join(lines[1:]).strip()
    parts = [p.strip() for p in first.split("·")]
    direction = " · ".join(parts[2:]) if len(parts) > 2 else ""
    if first.startswith("ALL FOUR"):
        direction = " · ".join(p for p in parts if not p.startswith("SPEAKER") and not re.match(r"[0-9:–]+$", p))
    if direction:
        out.append(f'<p class="dir">{E(direction)}</p>')
    for para in re.split(r"\n\s*\n", rest):
        para = para.strip()
        if not para:
            continue
        lab = re.match(r"^(HAND-OFF|SAY|IF [A-Z ’'-]+|Before you start|SPEAKER \d|ALL FOUR, together)(:| while[^:]*:)\s*", para)
        cls = "say"
        label = ""
        if lab:
            label = lab.group(0).rstrip(": ").strip()
            para = para[lab.end():]
            if label.startswith("HAND-OFF") or label.startswith("IF") or label.startswith("Before"):
                cls = "cue"
        body = E(para)
        body = re.sub(r"\[(Speaker \d|Team name|College|morning / afternoon)\]", r'<span class="ph">\1</span>', body)
        body = re.sub(r"\[([^\]]+)\]", r'<span class="act">[\1]</span>', body)
        body = body.replace("\n", "<br>")
        if not lab and (para.startswith("IF ") or (para.startswith("[") and para.endswith("]"))):
            cls = "cue"
        out.append(f'<p class="{cls}">' + (f'<b class="lab">{E(label)}</b> ' if label else "") + body + "</p>")
    return "\n".join(out)


def mmss(t):
    m, s = t.split(":")
    return int(m) * 60 + int(s)


rows = []
for i, sid in enumerate(order):
    n = notes(sid)
    spk, t0, t1 = speaker_of(n)
    rows.append(dict(i=i + 1, sid=sid, title=TITLES.get(sid, sid), spk=spk, t0=t0, t1=t1, notes=n,
                     dur=mmss(t1) - mmss(t0), shot=(SHOTS / f"{i + 1:02d}_{sid}.png").as_uri()))

# ------------------------------------------------------------------------------------------------ pieces
run_rows = "\n".join(
    f'<tr><td class="num">{r["i"]}</td><td><b>{E(r["title"])}</b></td>'
    f'<td><span class="chip" style="background:{SPK[r["spk"]]}">Speaker {r["spk"]}</span></td>'
    f'<td class="num">{r["t0"]}</td><td class="num">{r["t1"]}</td><td class="num">{r["dur"] // 60}:{r["dur"] % 60:02d}</td></tr>'
    for r in rows)

script_blocks = []
for r in rows:
    script_blocks.append(f"""
<div class="slide">
  <div class="slidehead">
    <img src="{r['shot']}" alt="Slide {r['i']}">
    <div>
      <p class="kicker">Slide {r['i']} of {len(rows)}</p>
      <h3>{E(r['title'])}</h3>
      <p><span class="chip" style="background:{SPK[r['spk']]}">Speaker {r['spk']}</span>
         <span class="time">{r['t0']} – {r['t1']} · {r['dur'] // 60}:{r['dur'] % 60:02d} min</span></p>
    </div>
  </div>
  <div class="script">{fmt_script(r['notes'])}</div>
</div>""")


def cards(spk):
    mine = [r for r in rows if r["spk"] == spk]
    items = "".join(f'<li><b>{r["t0"]} · Slide {r["i"]} · {E(r["title"])}</b><br>{E(CUES[r["sid"]])}</li>' for r in mine)
    return f"""<div class="cuecard"><div class="cuehead" style="background:{SPK[spk]}">Speaker {spk} · cue card
    <span>{mine[0]['t0']} – {mine[-1]['t1']}</span></div><p class="role">{E(ROLES[spk][1])}</p><ol>{items}</ol>
    <p class="handoff"><b>Hand-off line:</b> {E(HANDOFF[spk])}</p></div>"""


CUES = {
    "cover": "Collapsed building, someone alive under it. Team names. “This is ResQBot Mini.” Promise: live demo.",
    "golden": "72 h golden window (pause). Bhuj 2001 ~20,000. Türkiye–Syria 2023 50,000+. “How do we find people faster, safely?”",
    "problem": "4 reasons: rescuers risk lives · survivors hidden/unconscious · heat tools cost lakhs · networks fail.",
    "gap": "Hands, dogs, ₹25k camera, ₹1 lakh drone, lakh+ robots. “Nothing in between.” → hand to Speaker 2.",
    "solution": "Hold the robot up. Shoebox, < 1 kg. Front to back: heat sensor on servos, camera, ultrasonic, PIR, gas, beacon, Uno.",
    "mission": "Count on fingers: Deploy · Search · Detect · Confirm · Alert · Report.",
    "architecture": "Uno = brain (senses + controls). ESP32-CAM = eyes and voice (video, Wi-Fi, dashboard). One cable + checksum.",
    "cost": "₹3,589 (₹4,684 all new). One ₹25k camera = 7 robots. → switch robot ON, hand to Speaker 3.",
    "sweep": "Forehead-thermometer idea, ₹759. Swing it: 15 angles × 2 heights = 30 pixels, ~5 s. Blue room, orange person.",
    "tube": "Hold up the tube. 90° → 25°. Range 0.4 m → ~1.5 m (model; test T2). “Best upgrade: black paper.”",
    "score": "Heat contrast (≤42 °C) · size · warmer when closer · movement. 60 alert / 35 possible / below rejected.",
    "unconscious": "Unconscious still passes 60 → “not moving”. Fakes rejected: heater, cup, sunny wall, fire = warning. 12/12 tests.",
    "dashboard": "No app, no internet. Radar + video + alert + E-STOP. “Let’s see it for real.” → Speaker 4.",
    "demo": "Auto search → sweep → orange → turn, creep to 35 cm → wait 5 s → RED BANNER. Read %. Survivor out. Acknowledge. E-STOP.",
    "safety": "Survivors (slow, 35 cm, never < 10 cm) · rescuers (goes first, warnings) · robot (E-STOP, 0.8 s, battery). A scout, not a replacement.",
    "impact": "Earthquakes, smoke, floods, tunnels, NDRF/NCC drills, labs. Faster · safer · affordable. SDG 3, 9, 11.",
    "future": "Array sensor · tracks · microphone + CO₂ · map · LoRa · swarm. Wave team forward.",
    "close": "Every hour counts, every rescuer counts. ALL: “Send the robot first.” “Thank you — questions?”",
}
ROLES = {
    "1": ("The problem", "Opens the talk and owns the ‘why’. During the demo: the survivor behind the cardboard rubble."),
    "2": ("The robot", "Explains the hardware, mission and cost. Switches the robot on at 7:00 and is the robot handler during the demo."),
    "3": ("The intelligence", "Explains the thermal sweep, score and dashboard. Runs the laptop: switches the projector to the dashboard and back."),
    "4": ("Demo and impact", "Runs the live demo from the phone, then safety, impact, future and the close. Leads Q&A."),
}
HANDOFF = {
    "1": "“To show you how it works, here’s [Speaker 2].”",
    "2": "“So how does a three-thousand-rupee robot see body heat? [Speaker 3] will show you.”",
    "3": "“That’s enough slides. Let’s see it for real. [Speaker 4]?”",
    "4": "“Thank you. We’re happy to take your questions.”",
}

QA = [
    ("1", "How is this different from other student rescue robots?",
     "Three things: the four-clue confidence score that still finds unconscious people and rejects heaters and reflections; the robot "
     "parks beside the survivor as a light-and-sound marker; and it needs no internet or app, because the dashboard lives inside the robot."),
    ("1", "Who would actually use it?",
     "The people who arrive first and have the least equipment: local fire stations, civil-defence and NCC/NSS volunteers, NGOs, and "
     "training teams. It is a first-look scout that tells them where to dig first, not a replacement for NDRF."),
    ("2", "Why two boards — why not just the ESP32-CAM?",
     "The camera uses almost every pin of the ESP32-CAM, and its pins are 3.3 V. The Uno has 5 V pins for all the sensors, and splitting "
     "the jobs keeps motor and sensor control steady while the ESP32-CAM handles Wi-Fi and video. Both are boards most labs already own."),
    ("2", "How long does the battery last?",
     "It runs on a 7.4 V, 2500 mAh pack. Our design target is at least 45 minutes of continuous searching (test T12). [Say your measured "
     "time here.] It stops itself at 6.8 V to protect the cells."),
    ("2", "Could you mass-produce it? What would it cost at scale?",
     "Every part is a standard module, so a kit version would cost less than our ₹3,589 retail bill. The design is open, so any lab can "
     "build it today."),
    ("2", "What was the hardest problem you solved?",
     "Reliable control over Wi-Fi. In testing, the buttons sometimes stopped working while the video kept playing. We found three causes: "
     "the page fell into demo mode after two missed replies, the camera board ran out of network sockets, and garbled serial commands. "
     "We fixed all three and added a checksum to every command."),
    ("3", "Why not use a real thermal camera sensor?",
     "An 8×8 or 32×24 thermal array costs several times more than the whole sensor budget. Sweeping one ₹759 sensor gives 30 pixels — "
     "enough to detect a person and point to them. The array is our first upgrade."),
    ("3", "What is the detection range?",
     "Our geometric model estimates about 1.5 m for a person lying down with the 25° tube, and about 0.4 m without it. [If you have "
     "measured it in test T2, give the measured number instead.] Beyond that, the robot drives closer and sweeps again."),
    ("3", "What if the room is already near body temperature?",
     "The robot compares against the median of the whole sweep, so a warm room raises the baseline, but the contrast gets smaller. Then "
     "the live video and motion clue matter more. A thermal array sensor would help most here."),
    ("3", "Would it raise an alarm for a dog or a cat?",
     "Possibly, because an animal is warm and body-sized. That is why the alert comes with live video: the rescuer looks before acting. "
     "Treat an alert as ‘check here first’, not as proof."),
    ("3", "How does it know the direction and distance?",
     "Direction comes from the angles of the warm cells, weighted by how warm they are. Distance comes from the ultrasonic sensor as it "
     "creeps forward and stops at 35 cm."),
    ("3", "What have you actually tested?",
     "Both programs compile and run on the boards; the detection logic passes all 12 simulated scenarios; the dashboard was tested on "
     "phone and laptop; [add the results of the tests T1–T13 you have run]."),
    ("4", "Does it work in smoke?",
     "Infrared sees through darkness, dust and light smoke far better than a normal camera. Dense smoke and flames reduce accuracy, and "
     "the MQ-2 sensor warns rescuers about smoke and gas. It must not be used in explosive atmospheres."),
    ("4", "What happens if it loses Wi-Fi?",
     "It stops by itself within 0.8 seconds if commands stop arriving. In auto mode it keeps searching and the alert waits on screen when "
     "the phone reconnects. Range is about 20–50 m; a LoRa relay is on our roadmap."),
    ("4", "Can it climb real rubble?",
     "Not yet. It handles small obstacles and flat voids. Tracks and higher clearance are the next chassis step."),
    ("4", "Is the live video private?",
     "Yes. Everything stays on the robot’s own Wi-Fi between the robot and the rescuer’s phone. Nothing is sent to the internet."),
]
qa_rows = "\n".join(
    f'<div class="qa"><p class="q"><span class="chip" style="background:{SPK[s]}">S{s}</span> {E(q)}</p>'
    f'<p class="a">{re.sub(r"\[([^\]]+)\]", r"<span class=act>[\1]</span>", E(a))}</p></div>' for s, q, a in QA)

STAGE_SVG = """
<svg viewBox="0 0 900 470" xmlns="http://www.w3.org/2000/svg" font-family="Public Sans, Arial, sans-serif">
 <rect width="900" height="470" fill="#FBFAF6"/>
 <rect x="230" y="20" width="440" height="56" rx="6" fill="#0F1420"/><text x="450" y="54" fill="#F4F1EA" font-size="17" text-anchor="middle" font-weight="700">PROJECTOR SCREEN</text>
 <rect x="40" y="110" width="820" height="250" rx="10" fill="#EFE9DC" stroke="#CFC6B4"/>
 <text x="56" y="134" fill="#6B7280" font-size="13" font-weight="700" letter-spacing="2">STAGE</text>
 <rect x="80" y="170" width="170" height="80" rx="8" fill="#fff" stroke="#9AA3B2"/><text x="165" y="198" font-size="14" text-anchor="middle" font-weight="700" fill="#1D2433">Demo table</text>
 <text x="165" y="218" font-size="12" text-anchor="middle" fill="#4A5568">laptop → projector (HDMI)</text><text x="165" y="236" font-size="12" text-anchor="middle" fill="#4A5568">spare battery, backup clip</text>
 <circle cx="300" cy="300" r="20" fill="#FF6B1A"/><text x="300" y="305" font-size="12" text-anchor="middle" fill="#fff" font-weight="700">BOT</text>
 <text x="300" y="342" font-size="12" text-anchor="middle" fill="#1D2433">robot start mark (tape)</text>
 <path d="M322 300 L520 300" stroke="#FF6B1A" stroke-width="3" stroke-dasharray="8 6"/>
 <text x="420" y="290" font-size="12" text-anchor="middle" fill="#B2410C">≈ 1.2 m, clear floor</text>
 <rect x="540" y="240" width="40" height="110" fill="#C8A57A" stroke="#8C6B43"/><rect x="640" y="240" width="40" height="110" fill="#C8A57A" stroke="#8C6B43"/>
 <rect x="580" y="320" width="60" height="30" fill="#C8A57A" stroke="#8C6B43"/>
 <circle cx="610" cy="290" r="18" fill="#2F6FD6"/><text x="610" y="295" font-size="12" text-anchor="middle" fill="#fff" font-weight="700">S1</text>
 <text x="610" y="230" font-size="12" text-anchor="middle" fill="#1D2433">“rubble”: open gap faces the robot</text>
 <circle cx="760" cy="200" r="18" fill="#C2255C"/><text x="760" y="205" font-size="12" text-anchor="middle" fill="#fff" font-weight="700">S4</text>
 <text x="760" y="236" font-size="12" text-anchor="middle" fill="#1D2433">presenter spot</text><text x="760" y="252" font-size="12" text-anchor="middle" fill="#1D2433">(phone in hand)</text>
 <circle cx="200" cy="300" r="18" fill="#1BAF7A"/><text x="200" y="305" font-size="12" text-anchor="middle" fill="#fff" font-weight="700">S3</text>
 <text x="160" y="342" font-size="12" text-anchor="middle" fill="#1D2433">at the laptop</text>
 <circle cx="420" cy="200" r="18" fill="#2F6FD6" fill-opacity=".0" stroke="#2F6FD6" stroke-dasharray="3 3"/>
 <circle cx="450" cy="160" r="18" fill="#2F6FD6"/><text x="450" y="165" font-size="12" text-anchor="middle" fill="#fff" font-weight="700">S2</text>
 <text x="450" y="196" font-size="12" text-anchor="middle" fill="#1D2433">beside the robot path</text>
 <rect x="40" y="390" width="820" height="60" rx="8" fill="#E2E6EE"/><text x="450" y="426" font-size="15" text-anchor="middle" fill="#4A5568" font-weight="700">AUDIENCE · about 1,000 students</text>
 <text x="450" y="378" font-size="12" text-anchor="middle" fill="#6B7280">front edge of the stage: speakers present from here, facing the audience, screen behind</text>
</svg>"""

# ------------------------------------------------------------------------------------------------ document
CSS = """
@page{size:A4;margin:16mm 15mm 18mm}
*{box-sizing:border-box}
body{font-family:'Public Sans',Arial,sans-serif;color:#1D2433;font-size:10.5pt;line-height:1.5;margin:0}
h1,h2,h3{font-family:'Oswald','Arial Narrow',sans-serif;font-weight:600;line-height:1.15;margin:0}
h2{font-size:22pt;margin:0 0 3mm;color:#0F1420;break-after:avoid}
h2 .n{color:#FF6B1A;margin-right:3mm}
h3{font-size:14pt;margin:4mm 0 2mm;break-after:avoid}
p{margin:0 0 2.2mm}
.chapter{break-before:page}
.lead{font-size:12pt;color:#3D4656;margin-bottom:5mm}
table{width:100%;border-collapse:collapse;margin:2mm 0 5mm;font-size:9.8pt}
th{background:#0F1420;color:#F4F1EA;text-align:left;padding:2mm 2.5mm;font-weight:600}
td{padding:1.8mm 2.5mm;border-bottom:1px solid #E1DCD0;vertical-align:top}
tr{break-inside:avoid}
table.tight td{padding:1mm 2.5mm}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.chip{display:inline-block;color:#fff;font-weight:700;font-size:8.5pt;padding:.5mm 2.2mm;border-radius:3mm;white-space:nowrap}
.box{border:1px solid #E1DCD0;border-left:4px solid #FF6B1A;background:#FBFAF6;padding:3mm 4mm;margin:3mm 0 4mm;border-radius:2mm;break-inside:avoid}
.box.red{border-left-color:#E5383B;background:#FFF5F5}
.box.blue{border-left-color:#2F6FD6;background:#F4F8FF}
.box b.t{display:block;font-family:'Oswald',sans-serif;font-weight:600;font-size:12pt;margin-bottom:1mm}
ul,ol{margin:0 0 3mm;padding-left:5.5mm}
li{margin-bottom:1.2mm}
.cover{height:262mm;background:#0F1420;color:#F4F1EA;margin:-16mm -15mm 0;padding:22mm 18mm;display:flex;flex-direction:column;justify-content:space-between}
.cover .eyebrow{color:#FF6B1A;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;font-size:10pt}
.cover h1{font-size:54pt;text-transform:uppercase;line-height:1;margin:5mm 0}
.cover .sub{font-size:16pt;color:#C3CCDA;max-width:150mm}
.cover img{width:100%;border-radius:4mm}
.facts{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm;margin-top:8mm}
.facts div{background:#182031;border:1px solid #2A3342;border-radius:3mm;padding:3mm 4mm}
.facts b{display:block;font-family:'Oswald',sans-serif;font-size:22pt;color:#FF6B1A;line-height:1.1}
.facts span{font-size:9pt;color:#B8C2D3}
.toc li{margin-bottom:1.6mm;font-size:11pt}
.roles{display:grid;grid-template-columns:1fr 1fr;gap:3mm;margin:3mm 0 4mm}
.role{border:1px solid #E1DCD0;border-radius:2.5mm;padding:3mm 4mm;break-inside:avoid}
.role h3{margin:1mm 0}
.slide{break-inside:avoid-page;border-top:2px solid #0F1420;padding-top:3mm;margin-bottom:6mm}
.slidehead{display:flex;gap:5mm;align-items:center;margin-bottom:2.5mm;break-inside:avoid;break-after:avoid}
.slidehead img{width:78mm;border-radius:1.5mm;border:1px solid #D7D0C2}
.slidehead h3{font-size:18pt;margin:1mm 0 2mm}
.kicker{font-size:8.5pt;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#B2410C;margin:0}
.time{font-size:9.5pt;color:#4A5568;margin-left:2mm}
.script p{margin:0 0 2.2mm}
.script .say{font-size:11pt;line-height:1.55}
.script .dir,.script .cue{font-size:9.5pt;color:#4A5568;background:#F3F1EA;border-radius:1.5mm;padding:1.5mm 2.5mm}
.script .cue{background:#FFF1E6;color:#5C2A0A}
.act{color:#B2410C;font-style:italic;font-size:9.5pt}
.ph{background:#FFE9A8;border-radius:1mm;padding:0 1mm;font-weight:600}
.lab{font-family:'Oswald',sans-serif;font-weight:600;color:#0F1420;letter-spacing:.5px;text-transform:uppercase;font-size:9.5pt}
.qa{break-inside:avoid;border-bottom:1px solid #E1DCD0;padding:2.2mm 0}
.q{font-weight:700;margin-bottom:1mm}
.a{color:#3D4656;margin:0}
.cuecard{border:2px solid #0F1420;border-radius:3mm;overflow:hidden;break-inside:avoid;margin-bottom:6mm}
.cuehead{color:#fff;font-family:'Oswald',sans-serif;font-size:16pt;padding:2.5mm 4mm;display:flex;justify-content:space-between}
.cuehead span{font-size:12pt;opacity:.9}
.cuecard .role{border:0;padding:2mm 4mm 0;color:#4A5568;font-size:9.5pt;margin:0}
.cuecard ol{padding:2mm 4mm 0 9mm;margin:0;font-size:10pt}
.cuecard li{margin-bottom:2mm}
.handoff{background:#F3F1EA;padding:2mm 4mm;margin:2mm 0 0;font-size:10pt}
.two{display:grid;grid-template-columns:1fr 1fr;gap:5mm}
.check li{list-style:none;margin-left:-5mm;padding-left:6mm;text-indent:-6mm}
.check li::before{content:"☐  ";color:#B2410C}
svg{width:100%;height:auto;border:1px solid #E1DCD0;border-radius:2mm}
.small{font-size:9pt;color:#4A5568}
"""

doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>ResQBot Mini — Stage Presentation Guide</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Oswald:wght@400..700&family=Public+Sans:wght@400;600;700&display=swap">
<style>{CSS}</style></head><body>

<section class="cover">
  <div>
    <p class="eyebrow">Stage presentation guide</p>
    <h1>ResQBot Mini</h1>
    <p class="sub">The full script, roles, live-demo runbook, backup plans, Q&amp;A answers and rehearsal plan for a 15-minute talk to 1,000 students.</p>
    <div class="facts">
      <div><b>15:00</b><span>minutes on stage, plus Q&amp;A</span></div>
      <div><b>4</b><span>speakers, one section each</span></div>
      <div><b>18</b><span>slides, script in every note</span></div>
      <div><b>2:30</b><span>live robot demo</span></div>
    </div>
  </div>
  <img src="{(SHOTS / '14_demo.png').as_uri()}" alt="">
  <p class="small" style="color:#9AA6B8">[Team name] · [College] · [Event and date] — replace the [brackets] everywhere with your real names before you print.</p>
</section>

<section class="chapter">
<h2><span class="n">0</span>How to use this guide</h2>
<p class="lead">Everything you need for the stage is here. Read sections 1–3 together as a team, then each speaker learns their part from section 4 and their cue card in section 11.</p>
<ol class="toc">
  <li><b>Run of show</b> — who speaks when, to the second</li>
  <li><b>Team roles and stage layout</b> — where everyone stands and what they do during the demo</li>
  <li><b>The story</b> — the one message the audience must remember</li>
  <li><b>Full script</b> — every word, slide by slide, with stage directions</li>
  <li><b>Hand-offs</b> — how the clicker and the stage pass between speakers</li>
  <li><b>Live demo runbook</b> — setup timeline and the exact on-stage steps</li>
  <li><b>Backup plans</b> — what to say and do when something fails</li>
  <li><b>Q&amp;A bank</b> — 16 likely questions, who answers, and the answer</li>
  <li><b>Presenting to 1,000 people</b> — voice, microphone, eyes, body, nerves</li>
  <li><b>Rehearsal plan and day-of checklist</b></li>
  <li><b>Cue cards</b> — one printable card per speaker</li>
</ol>
<div class="box"><b class="t">Where the slides are</b>
The deck is the “ResQBot Mini — Stage Presentation” artifact on claude.ai. The speaker notes in it are this same script.
<b>Before the event, download it as PDF (for presenting) and as PPTX (backup)</b> from the deck’s download/export menu, and copy both files to the
stage laptop. The stage laptop will be on the robot’s Wi-Fi, which has no internet, so the slides must be offline files.</div>
<div class="box blue"><b class="t">The words in the script</b>
Text in quotes is what you say. <span class="act">[Orange italics in brackets]</span> are actions. Grey and peach boxes are stage directions.
You don’t have to memorise every word — memorise the <b>first sentence</b> and the <b>last sentence</b> of each slide, and the order of
the ideas. Say the rest in your own words. That sounds more natural to 1,000 people than a recited text.</div>
</section>

<section class="chapter">
<h2><span class="n">1</span>Run of show</h2>
<p class="lead">Fifteen minutes, four sections, one live demo. Times are from the moment Speaker 1 starts talking.</p>
<table class="tight">
<tr><th class="num">#</th><th>Slide</th><th>Speaker</th><th class="num">Start</th><th class="num">End</th><th class="num">Length</th></tr>
{run_rows}
</table>
<h3>Timing checkpoints</h3>
<table>
<tr><th>Checkpoint</th><th class="num">Target</th><th>If you are late</th></tr>
<tr><td>Speaker 1 hands over (end of slide 4)</td><td class="num">3:30</td><td>Speaker 2 shortens slide 6 to the six step names only.</td></tr>
<tr><td>Speaker 2 hands over (end of slide 8)</td><td class="num">7:00</td><td>Speaker 3 says slide 10 in two sentences.</td></tr>
<tr><td>Demo starts (slide 14)</td><td class="num">10:30</td><td>Speaker 3 skips the twelve-scenario list on slide 12.</td></tr>
<tr><td>Back on slides after the demo</td><td class="num">13:00</td><td>Speaker 4 skips slide 17 (“What’s next”) with one line: “We have a clear roadmap — ask us about it.”</td></tr>
<tr><td>Last line, “Send the robot first.”</td><td class="num">15:00</td><td>Never cut the close.</td></tr>
</table>
<div class="box"><b class="t">Time signals</b>Ask a friend in the front row to hold up a card: <b>“5”</b> at 10:00 and <b>“1”</b> at 14:00. Speakers glance, don’t stare.</div>
</section>

<section class="chapter">
<h2><span class="n">2</span>Team roles and stage layout</h2>
<div class="roles">
{''.join(f'<div class="role"><span class="chip" style="background:{SPK[k]}">Speaker {k}</span><h3>{E(v[0])}</h3><p>{E(v[1])}</p></div>' for k, v in ROLES.items())}
</div>
<h3>Stage layout (seen from above)</h3>
{STAGE_SVG}
<ul style="margin-top:3mm">
  <li><b>Only one speaker at the front at a time.</b> The others stand to the side, still and attentive — the audience watches them too.</li>
  <li><b>The clicker</b> belongs to whoever is speaking. Hand it over physically, at the hand-off line (section 5).</li>
  <li><b>The rubble</b>: two tall boxes with a low box between them, making a “void” whose open side faces the robot. The infrared sensor cannot see
  through cardboard, so the survivor’s face and arms must be visible through the gap.</li>
  <li><b>Tape marks</b>: put tape on the floor for the robot’s start position and for where the survivor sits, about 1.2 m apart. Measure it in rehearsal.</li>
</ul>
</section>

<section class="chapter">
<h2><span class="n">3</span>The story</h2>
<p class="lead">A thousand students will forget most of the details. Make sure they remember one sentence and one moment.</p>
<div class="box"><b class="t">The one sentence</b>“A ₹3,589 robot that feels body heat can go into a collapsed building first — so rescuers don’t have to go in blind.”</div>
<div class="box red"><b class="t">The one moment</b>The red <b>SURVIVOR DETECTED</b> banner on the big screen while the beacon flashes, the buzzer sounds and your teammate climbs out of the rubble. Build the whole talk towards it.</div>
<h3>The arc</h3>
<table>
<tr><th>Part</th><th>Feeling we want</th><th>How</th></tr>
<tr><td>1 · Problem</td><td>“This matters, and it’s unfair.”</td><td>One image (someone alive under concrete), one number (72 h), real disasters, the price gap.</td></tr>
<tr><td>2 · Robot</td><td>“That’s clever — and cheap.”</td><td>Hold the real robot. Six simple steps. ₹3,589 = one seventh of a thermal camera.</td></tr>
<tr><td>3 · Intelligence</td><td>“I understand how it thinks.”</td><td>Forehead-thermometer comparison, the paper tube, four clues anyone can follow.</td></tr>
<tr><td>4 · Demo + impact</td><td>“I just saw it work.”</td><td>The live find, then honesty about limits and a memorable close said by all four.</td></tr>
</table>
<h3>Language rules for this audience</h3>
<ul>
  <li>Say it like you would to a friend: short sentences, everyday words. “Feels body heat”, not “detects infrared radiation”.</li>
  <li>Every technical term gets a picture: the servo sweep is “like turning your head slowly from left to right”.</li>
  <li>Numbers: round and few. “Three thousand five hundred rupees” on stage; the exact ₹3,589 is on the slide.</li>
  <li>Be honest about estimates: the range is “our model estimates”, until you have measured it.</li>
</ul>
</section>

<section class="chapter">
<h2><span class="n">4</span>Full script</h2>
<p class="lead">Every slide, in order, with the words to say and what to do. This is the same text as the speaker notes in the deck. <span class="ph">Yellow</span> marks a name to fill in.</p>
{''.join(script_blocks)}
</section>

<section class="chapter">
<h2><span class="n">5</span>Hand-offs</h2>
<p class="lead">Three hand-offs make or break how professional a team looks. Rehearse them more than anything else.</p>
<table>
<tr><th>When</th><th>Outgoing speaker says</th><th>Movement</th></tr>
<tr><td>3:30 · slide 4 → 5</td><td>{E(HANDOFF['1'])}</td><td>Speaker 2 walks in from the right as their name is said. Clicker passes hand to hand. Speaker 1 steps left, then quietly goes to the rubble.</td></tr>
<tr><td>7:00 · slide 8 → 9</td><td>{E(HANDOFF['2'])}</td><td>Speaker 3 takes the clicker. Speaker 2 goes to the demo table and switches the robot ON (it needs 3 minutes to warm up its motion sensor).</td></tr>
<tr><td>10:30 · slide 13 → 14</td><td>{E(HANDOFF['3'])}</td><td>Speaker 4 takes the clicker and the phone. Speaker 3 goes to the laptop, ready to switch the projector to the dashboard.</td></tr>
</table>
<ul>
  <li>The incoming speaker starts with a short thank-you (“Thank you, [name].”) and goes straight into their first line.</li>
  <li>Never turn your back on the audience to walk; walk on a slight diagonal.</li>
  <li>Don’t say “next slide please” — whoever speaks holds the clicker.</li>
</ul>
</section>

<section class="chapter">
<h2><span class="n">6</span>Live demo runbook</h2>
<p class="lead">The demo is the highlight and the biggest risk. Prepare it like a pilot’s checklist.</p>
<h3>What you need</h3>
<div class="two"><ul>
  <li>Robot, fully charged; spare charged battery pack</li>
  <li>Stage laptop with charger, HDMI cable and adapter</li>
  <li>Phone for Speaker 4 (controls the robot), charged, mobile data OFF</li>
  <li>Slides as PDF and PPTX on the laptop (offline)</li>
</ul><ul>
  <li>Backup demo video on the laptop desktop (record it in rehearsal)</li>
  <li>Cardboard “rubble”: two tall boxes, one low box</li>
  <li>Floor tape, a measuring tape, spare jumper wires, small screwdriver</li>
  <li>The robot’s Wi-Fi name and password on a sticky note</li>
</ul></div>
<h3>Setup timeline</h3>
<table>
<tr><th>When</th><th>Who</th><th>Do this</th></tr>
<tr><td>Day before, on the real stage</td><td>All</td><td>Full tech check: projector, microphones, robot Wi-Fi with the hall full of phones if possible. Do a thermal scan with nobody in front of the robot — stage lights heat the floor and boxes. If the empty scan shows warm patches, move the setup out of the spotlight.</td></tr>
<tr><td>T − 60 min</td><td>S2</td><td>Charge check: battery above 7.8 V on the dashboard. Upload nothing new on the event day.</td></tr>
<tr><td>T − 30 min</td><td>S3</td><td>Laptop: plugged in, notifications OFF (Focus/Do not disturb), sleep OFF, screen saver OFF, display set to <b>Duplicate</b>. Open the slides PDF full-screen. Open the backup video, paused.</td></tr>
<tr><td>T − 15 min</td><td>S2, S1</td><td>Place the robot on its tape mark, rubble on its mark. Sound check: hold the buzzer near a microphone (“Beep / call out”).</td></tr>
<tr><td>T − 10 min</td><td>S3, S4</td><td>Robot ON. Laptop and phone join Wi-Fi <b>ResQBot-01</b>; on Android tap “Keep connected” when it says no internet. Open <b>192.168.4.1</b> in the laptop browser, press F11 (full screen). Check the top pill: <b>“LIVE · car ✓”</b>. Then robot OFF to save battery, and switch the laptop back to the slides.</td></tr>
<tr><td>7:00 on stage</td><td>S2</td><td>Robot ON (the motion sensor needs about 30 s; the gas sensor 2–3 min). Mode stays <b>Manual</b>.</td></tr>
<tr><td>10:00 on stage</td><td>S1</td><td>Sit behind the rubble, face and arms toward the gap, as still as possible.</td></tr>
</table>
<h3>On stage, step by step (2 min 30 s)</h3>
<table>
<tr><th>#</th><th>Speaker 4 does</th><th>The screen shows</th><th>Speaker 4 says (short)</th></tr>
<tr><td>1</td><td>Clicks to slide 14</td><td>“Let’s find someone.”</td><td>“Behind those boxes is a ‘survivor’. The camera can’t see them. Let’s see if the robot can feel them. Switch to the robot, please.”</td></tr>
<tr><td>2</td><td>Nods to Speaker 3</td><td>S3 presses Alt+Tab: live dashboard</td><td>“This is the robot’s live screen: video top right, heat radar on the left.”</td></tr>
<tr><td>3</td><td>Taps <b>Auto search</b> on the phone</td><td>Radar fills in over about 5 s</td><td>“It sweeps left to right, floor and straight ahead. Blue is the stage…”</td></tr>
<tr><td>4</td><td>Points at the screen</td><td>Orange cells, a bearing line</td><td>“There — orange, to the [left/right]. Body heat.”</td></tr>
<tr><td>5</td><td>Steps aside so the audience sees the robot</td><td>State: turning, approaching, confirming</td><td>“It turns… creeps forward slowly… stops at 35 cm… and checks for five seconds.”</td></tr>
<tr><td>6</td><td>Waits for the banner</td><td><b>SURVIVOR DETECTED</b>, beacon and buzzer</td><td>“Survivor detected! Confidence [read %], [temperature], [moving / not moving]. [Name], you can come out!” Lead the applause.</td></tr>
<tr><td>7</td><td>Taps <b>Acknowledge</b>, then <b>E-STOP</b></td><td>Banner clears; STOPPED</td><td>“And if anything goes wrong — one tap. All of this, with no internet at all.”</td></tr>
<tr><td>8</td><td>Nods to Speaker 3</td><td>S3 presses Alt+Tab: slide 15</td><td>Continue with safety.</td></tr>
</table>
<div class="box"><b class="t">What makes the find reliable</b>
<ul style="margin:0">
<li>The survivor’s face and forearms face the robot through the gap; clothes are cooler than skin.</li>
<li>Keep warm things out of the robot’s 140° view: laptops, chargers, people standing nearby, spotlights on the floor.</li>
<li>About 1–1.5 m between the robot and the survivor, nothing in between. Rehearse on the same distance at least five times.</li>
<li>Speaker 4 stands behind the robot or to its side, never in front of it — a person in front is also warm.</li>
</ul></div>
</section>

<section class="chapter">
<h2><span class="n">7</span>Backup plans</h2>
<p class="lead">Things go wrong on big stages. The audience forgives a problem; they remember how calmly you handled it. Apologise at most once.</p>
<table>
<tr><th style="width:24%">If this happens</th><th style="width:38%">Say</th><th style="width:38%">Do</th></tr>
<tr><td>Robot finds nothing in 60 s</td><td>“Let’s help it — this is exactly why it has a manual mode.”</td><td>Tap Manual, drive toward the survivor with the arrows, then <b>Thermal scan</b>. Point out the orange cells.</td></tr>
<tr><td>It alerts on the wrong thing</td><td>“It flagged a warm spot — and that’s why the rescuer gets live video to check.”</td><td>Acknowledge, aim it at the survivor in Manual, scan again.</td></tr>
<tr><td>Pill shows <b>NO CONNECTION</b></td><td>“A thousand phones in one hall is harder for Wi-Fi than any collapsed building!”</td><td>Move the laptop and phone closer to the robot (under 3 m); wait 10 s. Still nothing: play the backup video.</td></tr>
<tr><td>Pill shows <b>CAR NOT ANSWERING</b></td><td>“The camera is fine; the robot’s brain has lost its cable. Let me show you a recorded run.”</td><td>Play the backup video. After the talk, check the D0/D1 wires and the Uno power.</td></tr>
<tr><td>Robot doesn’t switch on</td><td>“Even rescue robots need a fresh battery.”</td><td>Swap in the spare pack (S2). If it still won’t start: backup video.</td></tr>
<tr><td>Projector shows nothing after Alt+Tab</td><td>(Keep talking about what the robot is doing.)</td><td>S3 presses Win+P → Duplicate. Speaker 4 narrates from the phone screen meanwhile.</td></tr>
<tr><td>Microphone dies</td><td>Speak louder and slower, step to the front edge.</td><td>Take a teammate’s microphone; never stop to fix it on stage.</td></tr>
<tr><td>You forget your lines</td><td>Look at the slide, say its title in your own words, continue.</td><td>Teammates never whisper corrections on stage.</td></tr>
</table>
<div class="box red"><b class="t">Record the backup video in rehearsal</b>
During your best rehearsal, record the full demo with a phone: the robot finding the survivor and the screen with the red banner. Put the file on the
laptop desktop as <b>BACKUP_DEMO.mp4</b>. A 30-second clip is enough. If the Wi-Fi is truly hopeless, you can also show the dashboard’s demo mode:
open <b>4_EXTRAS/dashboard_demo.html</b> from the project zip — but always say it is a demo, never present it as the live robot.</div>
<h3>Reducing Wi-Fi trouble in a crowded hall</h3>
<ul>
  <li>The robot uses 2.4 GHz channel 6. If the stage check shows a weak link, change <b>WIFI_CHANNEL</b> to 1 or 11 at the top of the ESP32-CAM sketch, upload, and test again — the day before, not on the event day.</li>
  <li>Keep the laptop and phone within a few metres of the robot, with a clear line of sight.</li>
  <li>Only two devices on the robot’s Wi-Fi: the stage laptop and Speaker 4’s phone. Everyone else stays off it.</li>
</ul>
</section>

<section class="chapter">
<h2><span class="n">8</span>Q&amp;A bank</h2>
<p class="lead">Speaker 4 hosts: repeats each question into the microphone (so the whole hall hears it), then passes it to the owner. Answers are 20–40 seconds. Text in <span class="act">[brackets]</span> needs your real test results.</p>
{qa_rows}
<div class="box blue"><b class="t">When you don’t know</b>“That’s a great question — we haven’t tested that yet, and it’s exactly the kind of thing our test plan is for. Can we talk after the session?” Never guess a number.</div>
</section>

<section class="chapter">
<h2><span class="n">9</span>Presenting to 1,000 people</h2>
<div class="two">
<div>
<h3>Voice and microphone</h3>
<ul>
  <li>Hold a handheld mic two fingers below your chin and keep it there when you turn your head.</li>
  <li>Speak 20% slower than feels natural. A big hall echoes; fast speech turns to noise.</li>
  <li>Pause after every key number (72 hours, ₹3,589, “survivor detected”). Silence is how a big room absorbs a point.</li>
  <li>End sentences on a falling tone. Rising endings sound unsure.</li>
</ul>
<h3>Eyes</h3>
<ul>
  <li>Split the hall into left, centre and right, front and back. Give each zone a whole sentence.</li>
  <li>Look at the back rows more than the front: it makes your voice and posture lift.</li>
  <li>Glance at the screen only to point; never read from it.</li>
</ul>
<h3>Body</h3>
<ul>
  <li>Stand still while you make a point; move only between points.</li>
  <li>Open hands, at waist height. Pocket hands and crossed arms look nervous from far away.</li>
  <li>Point at the slide with an open hand, then turn back to the audience before you speak.</li>
</ul>
</div>
<div>
<h3>Nerves</h3>
<ul>
  <li>Before you walk on: breathe in for 4, hold for 4, out for 6 — three times.</li>
  <li>Know your first sentence cold. The first 20 seconds are the hardest; after that it flows.</li>
  <li>Find two friendly faces in the hall and talk to them.</li>
</ul>
<h3>As a team</h3>
<ul>
  <li>Same dress code: plain dark trousers and a team T-shirt or plain shirt. Nothing with big logos.</li>
  <li>When you’re not speaking, watch the speaker and react: nod, smile at the jokes.</li>
  <li>Use names on stage: “Thank you, Ananya” sounds like a team; “thank you” sounds like a relay.</li>
</ul>
<h3>Never</h3>
<ul>
  <li>Start with “So…”, “Umm, hello?” or “Is this working?” — start with your first line.</li>
  <li>Apologise for nerves, the slides or the time.</li>
  <li>Say “basically” or read long numbers aloud.</li>
  <li>Overclaim. Say what you measured; say “estimate” where it is one.</li>
</ul>
</div>
</div>
</section>

<section class="chapter">
<h2><span class="n">10</span>Rehearsal plan and day-of checklist</h2>
<table>
<tr><th>When</th><th>Session</th><th>Goal</th></tr>
<tr><td>Day −7</td><td>Table read (60 min)</td><td>All four read the script aloud with a timer. Cut or reword anything that runs long or sounds unnatural in your voice.</td></tr>
<tr><td>Day −5</td><td>Own part (each alone)</td><td>Learn your first and last sentences by heart and the order of your ideas. Record yourself on a phone once and watch it.</td></tr>
<tr><td>Day −4</td><td>Hand-offs + demo (90 min)</td><td>Run all three hand-offs ten times. Run the demo at least five times on the measured distance; record the best run as the backup video.</td></tr>
<tr><td>Day −3</td><td>Failure drill (45 min)</td><td>Someone secretly causes a failure (unplug Wi-Fi, drain the battery, hide the slide). Practise the Plan-B lines from section 7.</td></tr>
<tr><td>Day −2</td><td>Full dress run + Q&amp;A</td><td>In front of 5–10 friends, in your stage clothes, standing up, with a timer. Then 10 minutes of their toughest questions.</td></tr>
<tr><td>Day −1</td><td>On the real stage</td><td>Tech check (section 6), a full run with the projector, and a thermal scan under the stage lights.</td></tr>
<tr><td>Event day</td><td>Warm-up (10 min)</td><td>First lines only, and one hand-off. No new changes to code, slides or script.</td></tr>
</table>
<h3>Day-of checklist</h3>
<div class="two"><ul class="check">
  <li>Robot + charged battery + spare battery</li>
  <li>Battery charger and power strip</li>
  <li>Stage laptop + charger + HDMI + adapter</li>
  <li>Slides PDF and PPTX on the laptop desktop</li>
  <li>BACKUP_DEMO.mp4 on the laptop desktop</li>
  <li>Speaker 4’s phone, charged, mobile data off</li>
  <li>Clicker with fresh batteries</li>
</ul><ul class="check">
  <li>Cardboard rubble (3 boxes) + floor tape</li>
  <li>Screwdriver, spare jumper wires, insulating tape</li>
  <li>Printed cue cards (section 11) and this guide</li>
  <li>Water bottle for each speaker</li>
  <li>Same team clothes</li>
  <li>Laptop: notifications off, sleep off, display Duplicate</li>
  <li>Projector and microphone checked with the venue team</li>
</ul></div>
</section>

<section class="chapter">
<h2><span class="n">11</span>Cue cards</h2>
<p class="lead">Print this page and the next, cut along the card borders, and keep your card in your pocket. The keywords are your safety net, not a script.</p>
{cards("1")}{cards("2")}
<div class="chapter"></div>
{cards("3")}{cards("4")}
</section>

</body></html>"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(doc, encoding="utf-8")
print(OUT, len(doc) // 1024, "KB")
