
"""Detect vertical scrolling using finger configurations and hand movement."""


class SwipeDetector:
    """Detect scroll gestures using hand position and finger states."""

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

    def reset(self):
        """Reset movement tracking."""
        self.anchor_y = None
        self.armed = True
        self.invalid_frames = 0

    def update(self, hand_info: dict, finger_states: list[int]) -> str | None:
        """Return SCROLL_UP, SCROLL_DOWN, or None."""

        # Gesture 1: All five fingers open.
        # Gesture 2: Thumb closed, remaining four fingers open.

        scroll_down_gesture = finger_states == [1, 1, 1, 1, 1]
        scroll_up_gesture = finger_states == [0, 1, 1, 1, 1]

        valid_gesture = scroll_down_gesture or scroll_up_gesture

        center = hand_info.get("center")

        if not valid_gesture or center is None or len(center) < 2:
            self.invalid_frames += 1

            if self.invalid_frames >= self.max_invalid_frames:
                self.reset()

            return None

        self.invalid_frames = 0
        current_y = center[1]

        # Establish the starting hand position.
        if self.anchor_y is None:
            self.anchor_y = current_y
            return None

        displacement = current_y - self.anchor_y

        # Rearm only after returning close to the starting position.
        if not self.armed:
            if abs(displacement) <= self.rearm_threshold:
                self.anchor_y = current_y
                self.armed = True
            return None

        # Ignore small movements.
        if abs(displacement) < self.movement_threshold:
            return None

        # Trigger only once per movement.
        self.armed = False

        # Negative Y displacement means hand moved UP.
        if displacement < 0 and scroll_down_gesture:
            return "SCROLL_DOWN"

        # Positive Y displacement means hand moved DOWN.
        if displacement > 0 and scroll_up_gesture:
            return "SCROLL_UP"

        return None
