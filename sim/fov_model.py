"""Rough range estimate for the MLX90614 with and without a viewing tube.

Simple geometric model, NOT a measurement: the sensor reports the average temperature of
everything inside its field of view (FOV), so a small warm body far away barely changes the
reading. Narrowing the FOV with a tube makes the body fill more of the view.

Assumptions: person lying on the floor, seen head/shoulders first (0.5 m wide, 0.25 m high),
average surface (skin + clothes) 31 C, rubble background 26 C, uniform sensitivity inside the FOV.
Run: python sim/fov_model.py  -> docs/images/fov_range.png
"""
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

W, H, T_BODY, T_BG, THRESHOLD = 0.5, 0.25, 31.0, 26.0, 1.5
OPTIONS = [("Bare sensor (90°)", 90, "#2a78d6"),
           ("Tube, 35° view", 35, "#eb6834"),
           ("Tube, 25° view (recommended)", 25, "#1baf7a")]


def delta(d, fov):
    aw = math.degrees(2 * math.atan(W / 2 / d))
    ah = math.degrees(2 * math.atan(H / 2 / d))
    frac = min(1, aw / fov) * min(1, ah / fov)
    return frac * (T_BODY - T_BG)


def max_range(fov):
    d = 0.1
    while delta(d, fov) >= THRESHOLD:
        d += 0.01
    return d


if __name__ == "__main__":
    dist = [0.2 + i * 0.02 for i in range(141)]          # 0.2 .. 3.0 m
    fig, ax = plt.subplots(figsize=(8, 4.4), dpi=200)
    fig.patch.set_facecolor("#ffffff")
    for label, fov, color in OPTIONS:
        ys = [delta(d, fov) for d in dist]
        ax.plot(dist, ys, color=color, lw=2)
        r = max_range(fov)
        ax.plot([r], [THRESHOLD], "o", ms=7, color=color, mec="white", mew=2, zorder=5)
        print(f"{label}: detectable to about {r:.2f} m")
        # label positions chosen to stay clear of the lines
        xy = {90: (0.46, 2.05), 35: (1.0, 4.3), 25: (1.56, 2.6)}[fov]
        ax.annotate(f"{label}\n≈ {r:.1f} m", (r, THRESHOLD), xytext=xy, fontsize=9, color="#333333",
                    arrowprops=dict(arrowstyle="-", color="#999999", lw=0.8) if fov == 35 else None)
    ax.axhline(THRESHOLD, color="#777777", lw=1, ls=(0, (4, 3)))
    ax.text(2.98, THRESHOLD - 0.28, "detection threshold +1.5 °C", ha="right", fontsize=9, color="#555555")
    ax.set_xlim(0.2, 3.0); ax.set_ylim(0, 5.2)
    ax.set_xlabel("Distance to person (m)", color="#444444")
    ax.set_ylabel("Reading above background (°C)", color="#444444")
    ax.set_title("Estimated thermal detection range (geometric model, lying person)", fontsize=11, loc="left", color="#222222")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#bbbbbb")
    ax.tick_params(colors="#555555")
    ax.grid(axis="y", color="#eeeeee")
    fig.tight_layout()
    out = Path(__file__).resolve().parent.parent / "docs" / "images" / "fov_range.png"
    fig.savefig(out)
    print("saved", out)
