"""Per-user calibration: guided steps and the maths that turns samples into settings.

This module has no Qt or camera code so it can be unit-tested. The
calibration window (src/gui/calibration_dialog.py) feeds it one hand sample
per camera frame.

What is measured
----------------
1. Point and hold still  -> fingertip jitter      -> jitter filter (dead zone)
2. Open palm             -> straight index angle  -> click bend angle (part 1)
3. Practise clicking     -> bent index angle      -> click bend angle (part 2)
4. Comfortable range     -> hand movement range   -> cursor speed

Scroll and zoom already scale with hand size, so they are not calibrated.
"""

import math
import statistics
from dataclasses import dataclass

from src.settings import clamp_setting


MOUSE_POSE = [0, 1, 0, 0, 0]
OPEN_PALM = [1, 1, 1, 1, 1]


@dataclass(frozen=True)
class CalibrationStep:
    key: str
    title: str
    instruction: str
    target: int          # samples (or bends) needed to finish the step
    unit: str = "frames"


STEPS = [
    CalibrationStep(
        "point_still",
        "Point and hold still",
        "Point with your index finger, with your thumb and other fingers "
        "tucked in (the cursor pose). Keep your hand as still as you can.",
        target=45,
    ),
    CalibrationStep(
        "open_palm",
        "Open your palm",
        "Hold your hand up with all five fingers open and straight.",
        target=30,
    ),
    CalibrationStep(
        "click_bends",
        "Practise clicking",
        "Keep your palm open and bend your index finger down and back up, "
        "the way you would to click. Do it 3 times, at a natural pace.",
        target=3,
        unit="bends",
    ),
    CalibrationStep(
        "move_range",
        "Show your comfortable range",
        "Make the cursor pose again and slowly move your hand to the left, "
        "right, top and bottom of the area you would comfortably use.",
        target=120,
    ),
]


def _percentile(values, pct):
    """Linear-interpolated percentile (pct in 0..100)."""
    data = sorted(values)
    if not data:
        raise ValueError("no data")
    if len(data) == 1:
        return data[0]
    pos = (len(data) - 1) * pct / 100.0
    lo = math.floor(pos)
    hi = min(lo + 1, len(data) - 1)
    return data[lo] + (data[hi] - data[lo]) * (pos - lo)


def _angle(a, b, c):
    """Angle ABC in degrees (same formula as src.main.calculate_angle)."""
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    mag_ba = math.hypot(*ba)
    mag_bc = math.hypot(*bc)
    if mag_ba == 0 or mag_bc == 0:
        return None
    cosine = (ba[0] * bc[0] + ba[1] * bc[1]) / (mag_ba * mag_bc)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def index_bend_angle(lm_list):
    return _angle(lm_list[5], lm_list[6], lm_list[8])


class Calibrator:
    """Collects samples step by step and computes calibrated settings."""

    # A bend is counted when the angle drops BEND_DOWN degrees below the
    # straight angle and then comes back within BEND_UP degrees of it.
    BEND_DOWN = 20
    BEND_UP = 10

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.step_index = 0
        self.skipped = set()

        self.frame_width = None
        self.frame_height = None

        self.still_tips = []
        self.open_angles = []
        self.click_angles = []
        self.range_tips = []

        self.bends = 0
        self._in_bend = False

    # -------------------------------------------------- step control

    @property
    def done(self):
        return self.step_index >= len(STEPS)

    @property
    def step(self):
        return None if self.done else STEPS[self.step_index]

    def count(self):
        key = self.step.key
        return {
            "point_still": len(self.still_tips),
            "open_palm": len(self.open_angles),
            "click_bends": self.bends,
            "move_range": len(self.range_tips),
        }[key]

    def progress(self):
        if self.done:
            return 1.0
        return min(1.0, self.count() / self.step.target)

    def step_complete(self):
        return not self.done and self.count() >= self.step.target

    def next_step(self):
        if not self.done:
            self.step_index += 1

    def skip_step(self):
        if not self.done:
            self.skipped.add(self.step.key)
            self.step_index += 1

    # -------------------------------------------------- samples

    def _straight_reference(self):
        if self.open_angles:
            return statistics.median(self.open_angles)
        return 170.0

    def feed(self, lm_list, finger_states, frame_width, frame_height):
        """Feed one frame. Returns True if it matched the pose for this step."""
        if self.done or lm_list is None or finger_states is None:
            return False
        if len(lm_list) < 21 or len(finger_states) != 5:
            return False

        self.frame_width = frame_width
        self.frame_height = frame_height
        key = self.step.key
        tip = (lm_list[8][0], lm_list[8][1])

        if key == "point_still":
            if list(finger_states) != MOUSE_POSE:
                return False
            self.still_tips.append(tip)
            return True

        if key == "open_palm":
            if list(finger_states) != OPEN_PALM:
                return False
            angle = index_bend_angle(lm_list)
            if angle is None:
                return False
            self.open_angles.append(angle)
            return True

        if key == "click_bends":
            # Thumb, middle, ring and pinky open; index may be bent.
            if [finger_states[i] for i in (0, 2, 3, 4)] != [1, 1, 1, 1]:
                return False
            angle = index_bend_angle(lm_list)
            if angle is None:
                return False
            self.click_angles.append(angle)

            straight = self._straight_reference()
            if not self._in_bend and angle < straight - self.BEND_DOWN:
                self._in_bend = True
            elif self._in_bend and angle > straight - self.BEND_UP:
                self._in_bend = False
                self.bends += 1
            return True

        if key == "move_range":
            if list(finger_states) != MOUSE_POSE:
                return False
            self.range_tips.append(tip)
            return True

        return False

    # -------------------------------------------------- results

    def results(self, current):
        """Return (new_values, notes).

        current: the settings to start from; only measured values change.
        notes:   human-readable lines describing each change or why a value
                 was kept.
        """
        values = dict(current)
        notes = []

        fw = self.frame_width or 640
        fh = self.frame_height or 480

        # Cursor speed from comfortable movement range.
        sensitivity = values["cursor_sensitivity"]
        if len(self.range_tips) >= 30:
            xs = [p[0] for p in self.range_tips]
            ys = [p[1] for p in self.range_tips]
            range_x = _percentile(xs, 95) - _percentile(xs, 5)
            range_y = _percentile(ys, 95) - _percentile(ys, 5)

            if range_x >= 0.12 * fw and range_y >= 0.08 * fh:
                # Moving across your comfortable range should move the cursor
                # across ~85% of the screen in one sweep.
                speed = 0.85 * ((fw / range_x) + (fh / range_y)) / 2
                sensitivity = clamp_setting("cursor_sensitivity", speed)
                values["cursor_sensitivity"] = sensitivity
                notes.append(f"Cursor speed set to {sensitivity:.2f}×.")
            else:
                notes.append(
                    "Movement range was too small to measure, so cursor "
                    "speed was not changed."
                )
        else:
            notes.append("Range step skipped, so cursor speed was not changed.")

        # Jitter filter from how much a still fingertip wobbles.
        if len(self.still_tips) >= 20:
            # The cursor follows a rolling median of the fingertip, so
            # measure the wobble that survives that smoothing.
            window = max(1, int(values.get("filter_frames", 5)))
            smoothed = []
            for i in range(window, len(self.still_tips) + 1):
                chunk = self.still_tips[i - window:i]
                smoothed.append((
                    statistics.median(p[0] for p in chunk),
                    statistics.median(p[1] for p in chunk),
                ))
            mx = statistics.median(p[0] for p in smoothed)
            my = statistics.median(p[1] for p in smoothed)
            wobble = [math.hypot(p[0] - mx, p[1] - my) for p in smoothed]
            jitter_cam = _percentile(wobble, 90)
            jitter_screen = jitter_cam * self.screen_width / fw * sensitivity
            dead_zone = int(max(2, min(12, round(jitter_screen))))
            values["dead_zone"] = clamp_setting("dead_zone", dead_zone)
            notes.append(f"Jitter filter set to {values['dead_zone']} px.")
        else:
            notes.append("Hold-still step skipped, so the jitter filter was not changed.")

        # Click bend angle halfway between straight and bent.
        if len(self.open_angles) >= 10 and len(self.click_angles) >= 10:
            straight = statistics.median(self.open_angles)
            bent = _percentile(self.click_angles, 10)
            if straight - bent >= 15:
                angle = int(round(max(110, min(165, (straight + bent) / 2))))
                values["click_bend_angle"] = clamp_setting("click_bend_angle", angle)
                notes.append(
                    f"Click bend angle set to {values['click_bend_angle']}° "
                    f"(straight ≈ {straight:.0f}°, bent ≈ {bent:.0f}°)."
                )
            else:
                notes.append(
                    "The index bend was too small to measure, so the click "
                    "angle was not changed."
                )
        else:
            notes.append("Click steps skipped, so the click angle was not changed.")

        return values, notes
