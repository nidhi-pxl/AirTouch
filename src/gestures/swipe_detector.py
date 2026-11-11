
"""Detect vertical scrolling using finger configurations and hand movement."""


class SwipeDetector:
    """Detect vertical scroll gestures using hand position and finger states."""

    def __init__(
        self,
        movement_threshold: int = 50,
        rearm_threshold: int = 10,
        max_invalid_frames: int = 3,
    ):
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

        displacement = current_y - self.anchor_y

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
