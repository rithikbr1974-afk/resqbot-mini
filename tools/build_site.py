"""Assembles website/ for static hosting (GitHub Pages, Netlify): index.html, images, PDFs and the dashboard demo."""
import shutil
from pathlib import Path

root = Path(__file__).resolve().parent.parent
site = root / "website"
body = (site / "site.html").read_text(encoding="utf-8")
(site / "index.html").write_text(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '</head>\n<body>\n' + body + '\n</body>\n</html>\n', encoding="utf-8")
(site / "images").mkdir(exist_ok=True)
(site / "files").mkdir(exist_ok=True)
for name in ["robot.png", "dashboard_desktop.png", "dashboard_phone.png"]:
    shutil.copy(root / "docs" / "images" / name, site / "images" / name)
for name in ["ResQBot_Proposal.pdf", "ResQBot_Components.pdf", "ResQBot_Schematics.pdf"]:
    shutil.copy(root / "docs" / name, site / "files" / name)
shutil.copy(root / "dashboard" / "index.html", site / "demo.html")
print("website ready:", sorted(p.name for p in site.rglob("*") if p.is_file()))
