"""AirTouch tuning settings: base values, the user's personal profile, storage.

There are two sets of values:

* BASE_SETTINGS - the values the team tuned during development. Always used
  when "personal settings" are switched off (e.g. the study's
  "Gesture without Calibration" condition).
* personal      - the user's own values, filled in by calibration and/or the
  sliders in the Settings window ("Gesture with Calibration").

The file is stored per Windows user at %APPDATA%\\AirTouch\\settings.json
(~/.config/AirTouch/settings.json elsewhere). Set AIRTOUCH_SETTINGS to use a
different file, e.g. one per study participant.
"""

import json
import os
from dataclasses import dataclass, field

from src import main as _defaults


# Base values. Mouse and click values come straight from src/main.py.
BASE_SETTINGS = {
    "cursor_sensitivity": _defaults.CURSOR_SENSITIVITY,      # 0.75
    "filter_frames": _defaults.FILTER_FRAMES,                # 5
    "dead_zone": _defaults.DEAD_ZONE,                        # 5 px
    "click_bend_angle": _defaults.LEFT_CLICK_BENT_ANGLE,     # 145 deg
    "click_confirm_frames": _defaults.LEFT_CLICK_CONFIRM_FRAMES,  # 3
    "scroll_threshold": 0.55,   # x hand size (SwipeDetector default)
    "zoom_threshold": 0.6,      # x hand size (ZoomDetector default)
    "pose_hold_frames": 5,      # right-click / undo hold (detector defaults)
}

# Allowed range, step and display info for each setting (used by the
# Settings window and to sanitise values loaded from disk).
SETTING_SPECS = {
    "cursor_sensitivity": dict(
        label="Cursor speed", minimum=0.3, maximum=3.0, step=0.05,
        fmt="{:.2f}×", help="How far the cursor moves for a hand movement.",
    ),
    "filter_frames": dict(
        label="Cursor smoothing", minimum=1, maximum=10, step=1,
        fmt="{:.0f} frames",
        help="Higher is steadier but responds a little later.",
    ),
    "dead_zone": dict(
        label="Jitter filter", minimum=0, maximum=20, step=1, fmt="{:.0f} px",
        help="Cursor ignores movements smaller than this.",
    ),
    "click_bend_angle": dict(
        label="Click bend angle", minimum=100, maximum=170, step=1,
        fmt="{:.0f}°",
        help="Bend your index finger below this angle to click. "
             "Higher = a smaller bend clicks.",
    ),
    "click_confirm_frames": dict(
        label="Click hold", minimum=1, maximum=8, step=1, fmt="{:.0f} frames",
        help="How long the bend must be held before it clicks.",
    ),
    "scroll_threshold": dict(
        label="Scroll distance", minimum=0.2, maximum=1.5, step=0.05,
        fmt="{:.2f}× hand",
        help="How far to move your palm to scroll, in hand sizes.",
    ),
    "zoom_threshold": dict(
        label="Zoom distance", minimum=0.2, maximum=1.5, step=0.05,
        fmt="{:.2f}× hand",
        help="How far to slide sideways to zoom, in hand sizes.",
    ),
    "pose_hold_frames": dict(
        label="Right-click / undo hold", minimum=2, maximum=15, step=1,
        fmt="{:.0f} frames",
        help="How long to hold the pinky or thumbs-down pose.",
    ),
}

INT_SETTINGS = {
    "filter_frames", "dead_zone", "click_bend_angle",
    "click_confirm_frames", "pose_hold_frames",
}


def clamp_setting(key, value):
    """Clamp a value to its allowed range and type."""
    spec = SETTING_SPECS[key]
    value = max(spec["minimum"], min(spec["maximum"], float(value)))
    return int(round(value)) if key in INT_SETTINGS else round(value, 2)


def settings_path():
    override = os.environ.get("AIRTOUCH_SETTINGS")
    if override:
        return override
    base = os.environ.get("APPDATA") or os.path.join(
        os.path.expanduser("~"), ".config"
    )
    return os.path.join(base, "AirTouch", "settings.json")


@dataclass
class UserSettings:
    use_personal: bool = False
    personal: dict = field(default_factory=lambda: dict(BASE_SETTINGS))
    calibrated_at: str | None = None
    seen_help: bool = False

    def effective(self) -> dict:
        """The values AirTouch should use right now."""
        return dict(self.personal) if self.use_personal else dict(BASE_SETTINGS)

    def profile_name(self) -> str:
        if not self.use_personal:
            return "Base settings"
        return "Calibrated" if self.calibrated_at else "Personal settings"

    def reset_to_base(self):
        """Forget calibration and adjustments; go back to the base settings."""
        self.use_personal = False
        self.personal = dict(BASE_SETTINGS)
        self.calibrated_at = None

    # -------------------------------------------------- storage

    @classmethod
    def load(cls, path=None) -> "UserSettings":
        path = path or settings_path()
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return cls()

        if not isinstance(data, dict):
            return cls()

        personal = dict(BASE_SETTINGS)
        stored = data.get("personal")
        if isinstance(stored, dict):
            for key in BASE_SETTINGS:
                if key in stored:
                    try:
                        personal[key] = clamp_setting(key, stored[key])
                    except (TypeError, ValueError):
                        pass

        calibrated_at = data.get("calibrated_at")
        return cls(
            use_personal=bool(data.get("use_personal", False)),
            personal=personal,
            calibrated_at=calibrated_at if isinstance(calibrated_at, str) else None,
            seen_help=bool(data.get("seen_help", False)),
        )

    def save(self, path=None) -> bool:
        path = path or settings_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "version": 1,
                        "use_personal": self.use_personal,
                        "personal": self.personal,
                        "calibrated_at": self.calibrated_at,
                        "seen_help": self.seen_help,
                    },
                    fh,
                    indent=2,
                )
            os.replace(tmp, path)
            return True
        except OSError:
            return False
