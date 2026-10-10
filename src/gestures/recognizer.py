
"""Recognize the static hand pose used by AirTouch."""

from typing import Optional


class GestureRecognizer:
    """
    Recognizes the pinch pose used by AirTouch zoom controls.

    Pinch distance and pinch start/release behavior should be handled by
    pinch_detector.py. Up/down scrolling should be handled by
    swipe_detector.py because it depends on movement across frames.
    """

    def __init__(self) -> None:
        """Initialize the supported AirTouch static gesture."""
        self.gestures = {
            "Pinch": None,
        }

    def register_gesture(self, name: str, template: list) -> None:
        """
        Register a finger-state template.

        Templates use [Thumb, Index, Middle, Ring, Pinky].
        Each value must be 0 (closed), 1 (open), or None (wildcard).

        Note: pinch is better detected geometrically, so registering a
        template alone does not implement pinch-distance detection.
        """
        if len(template) != 5:
            raise ValueError("Gesture template must contain exactly 5 elements.")

        if any(state not in (0, 1, None) for state in template):
            raise ValueError("Template values must be 0, 1, or None.")

        self.gestures[name] = template

    def recognize_gesture(
        self,
        finger_states: list[int],
        hand_info: dict,
    ) -> str:
        """
        Recognize supported static poses from finger states.

        Returns:
            "Unknown" when no supported template matches.

        Pinch detection is intentionally delegated to pinch_detector.py.
        """
        if len(finger_states) != 5:
            return "Unknown"

        for gesture_name, template in self.gestures.items():
            # Pinch is geometry-based, not a finger-state template.
            if template is None:
                continue

            if all(
                expected is None or expected == actual
                for expected, actual in zip(template, finger_states)
            ):
                return gesture_name

        return "Unknown"