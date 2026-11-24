"""Render the stage deck's slide files to PNGs (for the presenter guide), with headless Edge.

    python tools/render_slides.py <deck root holding project/>  ->  docs/presentation/slides/<id>.png

The Slides app draws icons and arrows itself; here they are simple stand-ins, which is fine for thumbnails."""
import json, re, subprocess, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
deck = Path(sys.argv[1]) / "project"
out = ROOT / "docs" / "presentation" / "slides"
out.mkdir(parents=True, exist_ok=True)
IMG = Path(sys.argv[2]) if len(sys.argv) > 2 else None   # folder with the uploaded images
BLOBS = {"ae9796d55022c957bfbf5670e1b18763": "dash_alert.png", "db8e05e1cde38849b83f099683c088bb": "robot_side.png",
         "3f51af87ce569e3b545eae751599e356": "block_diagram.png", "446faeffb3701c3378083d4f1de8e604": "flowchart.png",
         "9640bf36fde1259f7045606dd95c146b": "fov_range.png", "d985304d3e8b44d93105c9ef2ca500f1": "sensor_tube.png",
         "be998f99d84047287683c7015e1a5c45": "dashboard_phone.png"}

index = json.loads((deck / "deck.json").read_text(encoding="utf-8"))
order = index["order"]
css = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1920px;background:#000}
section{width:1920px;height:1080px;position:relative;overflow:hidden}
aside{display:none}
ul{padding-left:1.2em}
h1,h2,h3{font-weight:600}
table{border-collapse:collapse;width:100%}
th,td{padding:.35em .6em;border-bottom:1px solid rgba(128,128,128,.35);text-align:left;vertical-align:top}
x-icon{display:block;border-radius:50%;background:currentColor;opacity:.85}
x-shape{display:block;clip-path:polygon(0 30%,60% 30%,60% 0,100% 50%,60% 100%,60% 70%,0 70%)}
"""
for i, sid in enumerate(order):
    html = (deck / "slides" / f"{sid}.html").read_text(encoding="utf-8")
    for blob, name in BLOBS.items():
        html = html.replace(f"/_blob/{blob}", (IMG / name).as_uri() if IMG else "")
    fonts = "".join(f'<link rel="stylesheet" href="{f["href"]}">' for f in index["faces"].values())
    tmp = out / "_slide.html"
    tmp.write_text(f"<!doctype html><html><head><meta charset='utf-8'>{fonts}<style>{css}</style></head><body>{html}</body></html>",
                   encoding="utf-8")
    png = out / f"{i + 1:02d}_{sid}.png"
    subprocess.run(["powershell", "-NoProfile", "-File", str(ROOT / "tools" / "shot.ps1"), tmp.as_uri(), str(png), "1920", "1080", "1"],
                   check=True)
    Image.open(png).convert("RGB").save(png, optimize=True)
    tmp.unlink()
print(f"{len(order)} slides -> {out}")
