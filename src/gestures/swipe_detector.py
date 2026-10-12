
"""Detect vertical finger scrolling from index fingertip movement."""


class SwipeDetector:
    """Detect upward and downward index finger movements."""

    def __init__(
        self,
        movement_threshold: int = 50,
        rearm_threshold: int = 20,
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

        # Require the index finger to be extended.
        pointing = (
            len(finger_states) == 5
            and finger_states[1:] == [1, 0, 0, 0]
        )

        landmarks = hand_info.get("lm_list", [])

        if not pointing or len(landmarks) < 21:
            self.invalid_frames += 1

            # Tolerate brief recognition failures during fast movement.
            if self.invalid_frames >= self.max_invalid_frames:
                self.reset()

            return None

        self.invalid_frames = 0
        current_y = landmarks[8][1]

        # First valid frame establishes the reference.
        if self.anchor_y is None:
            self.anchor_y = current_y
            return None

        displacement = current_y - self.anchor_y

        # After a scroll, wait until the finger returns near
        # its starting position before allowing another event.
        if not self.armed:
            if abs(displacement) <= self.rearm_threshold:
                self.anchor_y = current_y
                self.armed = True
            return None

        # Ignore movements that are too small.
        if abs(displacement) < self.movement_threshold:
            return None

        # Fire only once during this movement.
        self.armed = False

        if displacement < 0:
            return "SCROLL_UP"

        return "SCROLL_DOWN"
