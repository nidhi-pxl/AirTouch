"""Detect one-shot pinch and spread gestures for zoom control."""

import math


class PinchDetector:
    """Detect zoom gestures and require a neutral reset between events."""

    def __init__(
        self,
        close_threshold=0.25,
        neutral_min=0.35,
        neutral_max=0.65,
        open_threshold=0.75,
    ):
        if not (
            0 <= close_threshold < neutral_min
            < neutral_max < open_threshold
        ):
            raise ValueError("Invalid gesture thresholds.")

        self.close_threshold = close_threshold
        self.neutral_min = neutral_min
        self.neutral_max = neutral_max
        self.open_threshold = open_threshold

        self.armed = False

    def reset(self):
        """Reset the detector state."""
        self.armed = False

    def get_normalized_distance(self, hand_info):
        """Measure thumb-index distance relative to hand size."""
        try:
            lm = hand_info["lm_list"]

            thumb = lm[4]
            index = lm[8]
            wrist = lm[0]
            middle_mcp = lm[9]

            pinch_distance = math.hypot(
                thumb[0] - index[0],
                thumb[1] - index[1],
            )

            hand_scale = math.hypot(
                wrist[0] - middle_mcp[0],
                wrist[1] - middle_mcp[1],
            )

            if hand_scale <= 0:
                return None

            return pinch_distance / hand_scale

        except (KeyError, TypeError, IndexError):
            return None

    def update(self, hand_info):
        """Return ZOOM_IN, ZOOM_OUT, or None for the current frame."""
        if hand_info is None:
            return None

        ratio = self.get_normalized_distance(hand_info)

        if ratio is None:
            return None

        # Return to neutral to allow the next gesture.
        if self.neutral_min <= ratio <= self.neutral_max:
            self.armed = True
            return None

        # Ignore gestures until neutral has been seen.
        if not self.armed:
            return None

        if ratio <= self.close_threshold:
            self.armed = False
            return "ZOOM_IN"

        if ratio >= self.open_threshold:
            self.armed = False
            return "ZOOM_OUT"

        return None