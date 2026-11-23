import math
import random

from src.calibration import STEPS, Calibrator
from src.settings import BASE_SETTINGS

MOUSE = [0, 1, 0, 0, 0]
PALM = [1, 1, 1, 1, 1]
PALM_INDEX_BENT = [1, 0, 1, 1, 1]


def make_hand(tip=(320, 200), bend=180.0):
    """Hand with index MCP(5) and PIP(6) fixed and the tip(8) placed so the
    5-6-8 angle equals `bend` degrees. The index tip lands at `tip`."""
    lm = [[0, 0, 0] for _ in range(21)]
    pip = (tip[0], tip[1] + 40)
    lm[6] = [pip[0], pip[1], 0]
    # MCP below the PIP; rotate the tip around the PIP by (180 - bend).
    lm[5] = [pip[0], pip[1] + 40, 0]
    theta = math.radians(180 - bend)
    lm[8] = [pip[0] + 40 * math.sin(theta), pip[1] - 40 * math.cos(theta), 0]
    if bend == 180.0:
        lm[8] = [tip[0], tip[1], 0]
    return lm


def run_full(cal, still_jitter=1.0, straight=175, bent=110, range_px=(320, 200)):
    rnd = random.Random(1)
    # 1. still
    while cal.step.key == "point_still" and not cal.step_complete():
        tip = (320 + rnd.gauss(0, still_jitter), 200 + rnd.gauss(0, still_jitter))
        cal.feed(make_hand(tip), MOUSE, 640, 480)
    cal.next_step()
    # 2. open palm
    while not cal.step_complete():
        cal.feed(make_hand(bend=straight + rnd.uniform(-2, 2)), PALM, 640, 480)
    cal.next_step()
    # 3. three bends
    for _ in range(3):
        for a in list(range(straight, bent, -5)) + list(range(bent, straight + 1, 5)):
            states = PALM_INDEX_BENT if a < 150 else PALM
            cal.feed(make_hand(bend=a), states, 640, 480)
    assert cal.step_complete()
    cal.next_step()
    # 4. range sweep
    i = 0
    while not cal.step_complete():
        t = i / 20.0
        x = 320 + range_px[0] / 2 * math.sin(t)
        y = 240 + range_px[1] / 2 * math.cos(t * 0.7)
        cal.feed(make_hand((x, y)), MOUSE, 640, 480)
        i += 1
    cal.next_step()
    assert cal.done


def test_steps_defined():
    assert [s.key for s in STEPS] == ["point_still", "open_palm", "click_bends", "move_range"]


def test_wrong_pose_is_not_counted():
    cal = Calibrator(1920, 1080)
    assert cal.feed(make_hand(), PALM, 640, 480) is False
    assert cal.count() == 0
    assert cal.feed(make_hand(), MOUSE, 640, 480) is True
    assert cal.count() == 1


def test_full_calibration_produces_sensible_values():
    cal = Calibrator(1920, 1080)
    run_full(cal)
    values, notes = cal.results(BASE_SETTINGS)

    # Bend angle halfway between ~175 straight and ~110 bent.
    assert 135 <= values["click_bend_angle"] <= 150
    # 320x200 px range in a 640x480 frame -> faster than the base 0.75.
    assert 1.0 < values["cursor_sensitivity"] <= 3.0
    assert 2 <= values["dead_zone"] <= 15
    # Uncalibrated values are untouched.
    assert values["scroll_threshold"] == BASE_SETTINGS["scroll_threshold"]
    assert len(notes) == 3


def test_shaky_hand_gets_bigger_dead_zone():
    steady = Calibrator(1920, 1080)
    run_full(steady, still_jitter=0.5)
    shaky = Calibrator(1920, 1080)
    run_full(shaky, still_jitter=4.0)
    assert shaky.results(BASE_SETTINGS)[0]["dead_zone"] > steady.results(BASE_SETTINGS)[0]["dead_zone"]


def test_small_bend_keeps_base_angle():
    cal = Calibrator(1920, 1080)
    for _ in range(40):
        cal.feed(make_hand(), MOUSE, 640, 480)
    cal.next_step()
    for _ in range(30):
        cal.feed(make_hand(bend=175), PALM, 640, 480)
    cal.next_step()
    for _ in range(30):
        cal.feed(make_hand(bend=168), PALM, 640, 480)   # barely bends
    cal.skip_step()
    cal.skip_step()
    values, notes = cal.results(BASE_SETTINGS)
    assert values["click_bend_angle"] == BASE_SETTINGS["click_bend_angle"]
    assert values["cursor_sensitivity"] == BASE_SETTINGS["cursor_sensitivity"]


def test_all_skipped_changes_nothing():
    cal = Calibrator(1920, 1080)
    while not cal.done:
        cal.skip_step()
    values, notes = cal.results(BASE_SETTINGS)
    assert values == BASE_SETTINGS
    assert len(notes) == 3
