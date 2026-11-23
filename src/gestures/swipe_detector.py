"""Detect vertical scrolling using finger configurations and hand movement."""

import math


class SwipeDetector:
    """Detect vertical scroll gestures using hand position and finger states.

    SCROLL_DOWN: all five fingers open, hand moves UP.
    SCROLL_UP  : thumb closed, four fingers open, hand moves DOWN.

    Movement is measured as a fraction of hand size (wrist -> middle MCP),
    like the zoom detector, so the same hand movement scrolls whether you sit
    close to the camera or far from it, and at any camera resolution.
    """

    def __init__(
        self,
        movement_threshold: float = 0.55,
        rearm_threshold: float = 0.12,
        max_invalid_frames: int = 3,
    ):
        # Both thresholds are multiples of hand size. 0.55 matches the old
        # 50-pixel threshold for a hand at a typical distance from a 640x480
        # webcam.
        self.movement_threshold = movement_threshold
        self.rearm_threshold = rearm_threshold
        self.max_invalid_frames = max_invalid_frames

        self.anchor_y = None
        self.armed = True
        self.invalid_frames = 0
        self.active_gesture = None

    def reset(self):
        """Reset movement tracking."""
        self.anchor_y = None
        self.armed = True
        self.invalid_frames = 0
        self.active_gesture = None

    @staticmethod
    def _hand_scale(lm_list) -> float:
        return math.hypot(
            lm_list[9][0] - lm_list[0][0],
            lm_list[9][1] - lm_list[0][1],
        )

    def update(self, hand_info: dict, finger_states: list[int]) -> str | None:
        """Return SCROLL_UP, SCROLL_DOWN, or None."""

        if hand_info is None or finger_states is None:
            self.reset()
            return None

        # Identify the gesture.
        if finger_states == [1, 1, 1, 1, 1]:
            gesture = "SCROLL_DOWN"

        elif finger_states == [0, 1, 1, 1, 1]:
            gesture = "SCROLL_UP"

        else:
            self.invalid_frames += 1

            if self.invalid_frames >= self.max_invalid_frames:
                self.reset()

            return None

        # Use palm landmarks instead of bounding-box center.
        lm_list = hand_info.get("lm_list")

        if lm_list is None or len(lm_list) < 10:
            self.reset()
            return None

        hand_scale = self._hand_scale(lm_list)

        if hand_scale <= 0:
            self.reset()
            return None

        self.invalid_frames = 0

        # Palm center: midpoint between wrist and middle MCP.
        current_y = (lm_list[0][1] + lm_list[9][1]) / 2

        # Reset anchor whenever the gesture changes.
        if gesture != self.active_gesture:
            self.active_gesture = gesture
            self.anchor_y = current_y
            self.armed = True
            return None

        if self.anchor_y is None:
            self.anchor_y = current_y
            return None

        # Displacement in hand sizes (negative = hand moved up).
        displacement = (current_y - self.anchor_y) / hand_scale

        # Rearm after returning close to the starting position.
        if not self.armed:
            if abs(displacement) <= self.rearm_threshold:
                self.anchor_y = current_y
                self.armed = True

            return None

        # Ignore small movements.
        if abs(displacement) < self.movement_threshold:
            return None

        # Five fingers open + hand moving UP.
        if gesture == "SCROLL_DOWN" and displacement < 0:
            self.armed = False
            return "SCROLL_DOWN"

        # Thumb closed + four fingers open + hand moving DOWN.
        if gesture == "SCROLL_UP" and displacement > 0:
            self.armed = False
            return "SCROLL_UP"

        return None
