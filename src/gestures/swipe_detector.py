
"""Detect vertical finger scrolling from index fingertip movement."""


class SwipeDetector:
    """Detect upward and downward index finger movement."""

    def __init__(self, movement_threshold: int = 50):
        self.movement_threshold = movement_threshold # move at least 50 pixels from the reference position before an event is generated
        self.previous_y = None # to know where y was previously to calculate movement

    def reset(self):
        """Forget the previous position."""
        self.previous_y = None

    def update(self, hand_info: dict, finger_states: list[int]) -> str | None:
        """
        Return SCROLL_UP, SCROLL_DOWN, or None.

        hand_info: dictionary returned by HandTracker.get_hands_info()
        finger_states: [Thumb, Index, Middle, Ring, Pinky]
        """
        # Require a pointing pose: index open, other fingers closed.
        if (
            len(finger_states) != 5
            or finger_states[1:] != [1, 0, 0, 0]
        ):
            self.reset()
            return None

        landmarks = hand_info.get("lm_list", [])

        if len(landmarks) < 21:
            self.reset()
            return None

        # Landmark 8 is the index fingertip.
        current_y = landmarks[8][1]

        # First frame establishes a reference position.
        if self.previous_y is None:
            self.previous_y = current_y
            return None

        delta_y = current_y - self.previous_y

        # Wait until the finger moves far enough.
        if abs(delta_y) < self.movement_threshold:
            return None

        # Update the reference so one movement triggers one event.
        self.previous_y = current_y

        if delta_y < 0:
            return "SCROLL_UP"

        return "SCROLL_DOWN"
