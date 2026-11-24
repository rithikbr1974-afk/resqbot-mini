"""Python mirror of firmware/ResQBot/detection.h, for testing and tuning on a laptop.

Keep the constants and steps in step with the C++ file. Run the tests with:
    python sim/test_detection.py
"""
from dataclasses import dataclass
from statistics import median

# --- same values as config.h ---
PAN_MIN, PAN_MAX, PAN_STEP, PAN_CENTER = 20, 160, 10, 90
COLS = (PAN_MAX - PAN_MIN) // PAN_STEP + 1          # 15
DELTA_MIN_C = 1.5
BODY_MAX_C = 42.0
FIRE_C = 55.0
MIN_BLOB_CELLS = 2
ALERT_SCORE, POSSIBLE_SCORE = 60, 35


@dataclass
class Finding:
    found: bool = False
    fire: bool = False
    background: float = float("nan")
    peak: float = float("nan")
    delta: float = 0.0
    cells: int = 0
    pan_angle: float = PAN_CENTER
    hottest: float = float("nan")
    row: int = 0

    @property
    def bearing(self):
        """Degrees from straight ahead; positive = robot's left."""
        return self.pan_angle - PAN_CENTER


def analyze_sweep(grid):
    """grid: list of rows, each a list of COLS temperatures (None = failed reading)."""
    f = Finding()
    vals = [t for row in grid for t in row if t is not None]
    if not vals:
        return f
    f.background = median(vals)
    f.hottest = max(vals)
    f.fire = f.hottest >= FIRE_C

    cols = len(grid[0])
    warm = [False] * cols
    col_delta = [0.0] * cols
    col_cells = [0] * cols
    col_row = [0] * cols
    for r, row in enumerate(grid):
        for c, t in enumerate(row):
            if t is None:
                continue
            d = t - f.background
            if d >= DELTA_MIN_C and t <= BODY_MAX_C:
                warm[c] = True
                col_cells[c] += 1
                if d > col_delta[c]:
                    col_delta[c], col_row[c] = d, r

    best_start, best_len, best_cells = -1, 0, 0
    c = 0
    while c < cols:
        if not warm[c]:
            c += 1
            continue
        s, cells = c, 0
        while c < cols and warm[c]:
            cells += col_cells[c]
            c += 1
        if cells > best_cells or (cells == best_cells and c - s > best_len):
            best_start, best_len, best_cells = s, c - s, cells
    if best_start < 0 or best_cells < MIN_BLOB_CELLS:
        return f

    span = range(best_start, best_start + best_len)
    wsum = sum(col_delta[c] for c in span)
    best_col = max(span, key=lambda c: col_delta[c])
    f.found = True
    f.cells = best_cells
    f.delta = col_delta[best_col]
    f.peak = f.background + f.delta
    f.row = col_row[best_col]
    f.pan_angle = sum(col_delta[c] * (PAN_MIN + c * PAN_STEP) for c in span) / wsum
    return f


def confidence_score(f, close_reading=None, motion=False):
    if not f.found:
        return 0
    thermal = 20 + min(20.0, (f.delta - DELTA_MIN_C) * 8.0)
    size = min(10.0, (f.cells - 1) * 5.0)
    rise = close_reading is not None and close_reading - f.peak >= 0.5 and close_reading <= BODY_MAX_C
    return min(100, int(thermal + size + (25 if rise else 0) + (25 if motion else 0)))


def verdict(score):
    if score >= ALERT_SCORE:
        return "SURVIVOR LIKELY"
    if score >= POSSIBLE_SCORE:
        return "possible survivor"
    return "rejected"
