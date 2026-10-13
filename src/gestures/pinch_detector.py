
"""Detect zoom using thumb-middle fingertip contact."""

import math


class PinchDetector:
    """Detect one-shot zoom gestures from thumb-middle distance."""

    def __init__(
        self,
        touch_threshold=0.30,
        release_threshold=0.45,
    ):
        if not 0 <= touch_threshold < release_threshold:
            raise ValueError("Invalid gesture thresholds.")

        self.touch_threshold = touch_threshold
        self.release_threshold = release_threshold
        self.previous_touch = None

    def reset(self):
        """Reset gesture tracking."""
        self.previous_touch = None

    def get_normalized_distance(self, hand_info):
        """Measure thumb-middle distance relative to hand size."""
        try:
            lm = hand_info["lm_list"]

            thumb = lm[4]
            middle_tip = lm[12]
            wrist = lm[0]
            middle_mcp = lm[9]

            distance = math.hypot(
                thumb[0] - middle_tip[0],
                thumb[1] - middle_tip[1],
            )

            hand_scale = math.hypot(
                wrist[0] - middle_mcp[0],
                wrist[1] - middle_mcp[1],
            )

            if hand_scale <= 0:
                return None

            return distance / hand_scale

        except (KeyError, TypeError, IndexError):
            return None

    def update(self, hand_info, finger_states):
        """Return ZOOM_IN, ZOOM_OUT, or None."""

        if hand_info is None or len(finger_states) != 5:
            self.reset()
            return None

        # Finger order: Thumb, Index, Middle, Ring, Pinky.
        # Index must be open; ring and pinky must be closed.
        valid_zoom_pose = (
            finger_states[1] == 1
            and finger_states[3] == 0
            and finger_states[4] == 0
        )

        if not valid_zoom_pose:
            self.reset()
            return None

        ratio = self.get_normalized_distance(hand_info)

        if ratio is None:
            self.reset()
            return None

        # Detect whether thumb and middle fingertips are touching.
        if ratio <= self.touch_threshold:
            touching = True
        elif ratio >= self.release_threshold:
            touching = False
        else:
            # Ignore the uncertain range between the thresholds.
            return None

        # Establish the initial state without triggering an action.
        if self.previous_touch is None:
            self.previous_touch = touching
            return None

        # No event if the contact state has not changed.
        if touching == self.previous_touch:
            return None

        self.previous_touch = touching

        if touching:
            return "ZOOM_OUT"

        return "ZOOM_IN"
