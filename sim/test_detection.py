"""Scenario tests for the survivor-detection logic. Run: python sim/test_detection.py"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from detection import COLS, analyze_sweep, confidence_score, verdict  # noqa: E402


def room(bg=26.0, noise=0.25, seed=1):
    rnd = random.Random(seed)
    return [[round(bg + rnd.uniform(-noise, noise), 2) for _ in range(COLS)] for _ in range(2)]


def put(grid, row, col, temp):
    grid[row][col] = temp
    return grid


def test_empty_room():
    f = analyze_sweep(room())
    assert not f.found and not f.fire
    assert confidence_score(f) == 0


def test_person_on_floor_right_side():
    g = room()
    for c, t in [(4, 29.4), (5, 31.2), (6, 29.8)]:
        put(g, 0, c, t)
    put(g, 1, 5, 28.4)
    f = analyze_sweep(g)
    assert f.found and f.row == 0
    assert -25 < f.bearing < -15, f.bearing          # columns 4-6 = 60-80 deg = right of centre
    assert f.cells == 4
    s = confidence_score(f)
    assert verdict(s) == "possible survivor", s       # heat alone is not enough for an alert


def test_unconscious_person_alert_without_motion():
    g = room()
    for c, t in [(7, 30.0), (8, 31.0)]:
        put(g, 0, c, t)
    f = analyze_sweep(g)
    s = confidence_score(f, close_reading=f.peak + 2.5, motion=False)
    assert verdict(s) == "SURVIVOR LIKELY", s         # warmer when closer is enough


def test_moving_person_scores_highest():
    g = room()
    for c, t in [(9, 30.5), (10, 32.0), (11, 30.2)]:
        put(g, 0, c, t)
        put(g, 1, c, t - 1.5)
    f = analyze_sweep(g)
    assert f.bearing > 0                              # left side
    s = confidence_score(f, close_reading=f.peak + 2, motion=True)
    assert s >= 90, s


def test_single_hot_pixel_is_noise():
    f = analyze_sweep(put(room(), 1, 3, 31.0))
    assert not f.found


def test_heater_is_not_a_person():
    g = room()
    for c in (6, 7, 8):
        put(g, 1, c, 48.0)
    f = analyze_sweep(g)
    assert not f.found and not f.fire


def test_fire_hot_spot_warning():
    g = room()
    put(g, 1, 12, 70.0)
    put(g, 1, 13, 64.0)
    f = analyze_sweep(g)
    assert f.fire and f.hottest == 70.0 and not f.found


def test_person_next_to_fire_still_found():
    g = room()
    put(g, 1, 13, 80.0)
    for c, t in [(2, 30.5), (3, 31.5)]:
        put(g, 0, c, t)
    f = analyze_sweep(g)
    assert f.fire and f.found and f.bearing < 0


def test_reflection_rejected_when_not_warmer_up_close():
    g = room()
    for c, t in [(7, 28.0), (8, 28.2)]:
        put(g, 0, c, t)
    f = analyze_sweep(g)
    s = confidence_score(f, close_reading=f.peak - 0.3, motion=False)
    assert verdict(s) == "rejected", s


def test_failed_readings_are_skipped():
    g = room()
    g[0][0] = g[1][14] = None
    for c, t in [(5, 30.0), (6, 30.5)]:
        put(g, 0, c, t)
    assert analyze_sweep(g).found


def test_hot_day_background():
    g = room(bg=36.0)                                 # summer rubble almost at body temperature
    for c, t in [(7, 38.0), (8, 38.4)]:
        put(g, 0, c, t)
    f = analyze_sweep(g)
    assert f.found and abs(f.background - 36.0) < 0.5


def test_largest_blob_wins():
    g = room()
    put(g, 0, 1, 29.0); put(g, 0, 2, 29.0)            # small blob
    for c in (9, 10, 11):                              # bigger blob
        put(g, 0, c, 30.0); put(g, 1, c, 29.0)
    f = analyze_sweep(g)
    assert f.cells == 6 and f.bearing > 0


if __name__ == "__main__":
    tests = [(n, fn) for n, fn in globals().items() if n.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {name}  {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
