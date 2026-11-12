"""Detect zoom gestures from sideways finger slides."""

import math


class ZoomDetector:
    """Fire ZOOM_IN or ZOOM_OUT once per sideways slide.

    ZOOM_IN : thumb out, other fingers closed, thumb slides RIGHT.
    ZOOM_OUT: index + middle fingers out (ring/pinky closed), slide LEFT.

    "Right" and "left" are directions in the mirrored webcam view
    (main.py flips the frame), so right means increasing x.

    Movement is measured as a fraction of hand size (wrist -> middle MCP),
    so thresholds work at any distance from the camera.
    """

    # [Thumb, Index, Middle, Ring, Pinky]; None means "don't care".
    ZOOM_IN_POSE = [1, 0, 0, 0, 0]
    ZOOM_OUT_POSE = [None, 1, 1, 0, 0]

    def __init__(
        self,
        movement_threshold: float = 0.6,
        rearm_threshold: float = 0.15,
        max_invalid_frames: int = 3,
        thumb_down_ratio: float = 0.25,
    ):
        self.movement_threshold = movement_threshold
        self.rearm_threshold = rearm_threshold
        self.max_invalid_frames = max_invalid_frames
        self.thumb_down_ratio = thumb_down_ratio

        self.anchor_x = None
        self.armed = True
        self.invalid_frames = 0
        self.active_gesture = None

    def reset(self):
        """Reset movement tracking."""
        self.anchor_x = None
        self.armed = True
        self.invalid_frames = 0
        self.active_gesture = None

    @staticmethod
    def _matches(template, finger_states) -> bool:
        return all(
            expected is None or expected == actual
            for expected, actual in zip(template, finger_states)
        )

    @staticmethod
    def _hand_scale(lm_list) -> float:
        return math.hypot(
            lm_list[9][0] - lm_list[0][0],
            lm_list[9][1] - lm_list[0][1],
        )

    def _thumb_points_down(self, lm_list, hand_scale) -> bool:
        """Same test as the thumbs-down (UNDO) detector, to avoid clashes."""
        dx = lm_list[4][0] - lm_list[2][0]
        dy = lm_list[4][1] - lm_list[2][1]  # positive = pointing down
        return dy > abs(dx) and dy / hand_scale > self.thumb_down_ratio

    def _identify(self, lm_list, finger_states, hand_scale):
        """Return "ZOOM_IN", "ZOOM_OUT" or None for the current pose."""
        if self._matches(self.ZOOM_IN_POSE, finger_states):
            if not self._thumb_points_down(lm_list, hand_scale):
                return "ZOOM_IN"
            return None

        if self._matches(self.ZOOM_OUT_POSE, finger_states):
            return "ZOOM_OUT"

        return None

    @staticmethod
    def _tracked_x(gesture, lm_list) -> float:
        if gesture == "ZOOM_IN":
            return lm_list[4][0]  # thumb tip
        # Midpoint of index tip (8) and middle tip (12).
        return (lm_list[8][0] + lm_list[12][0]) / 2

    def update(self, hand_info, finger_states):
        """Return ZOOM_IN, ZOOM_OUT, or None."""
        if hand_info is None or finger_states is None or len(finger_states) != 5:
            self.reset()
            return None

        lm_list = hand_info.get("lm_list")
        if lm_list is None or len(lm_list) < 21:
            self.reset()
            return None

        hand_scale = self._hand_scale(lm_list)
        if hand_scale <= 0:
            self.reset()
            return None

        gesture = self._identify(lm_list, finger_states, hand_scale)

        # Wrong pose: tolerate a few flickering frames, then reset.
        if gesture is None:
            self.invalid_frames += 1
            if self.invalid_frames >= self.max_invalid_frames:
                self.reset()
            return None

        self.invalid_frames = 0
        current_x = self._tracked_x(gesture, lm_list)

        # New pose: start measuring from here.
        if gesture != self.active_gesture:
            self.active_gesture = gesture
            self.anchor_x = current_x
            self.armed = True
            return None

        displacement = (current_x - self.anchor_x) / hand_scale

        # After firing, wait until the hand returns near the start.
        if not self.armed:
            if abs(displacement) <= self.rearm_threshold:
                self.anchor_x = current_x
                self.armed = True
            return None

        # Thumb slides right -> zoom in.
        if gesture == "ZOOM_IN" and displacement >= self.movement_threshold:
            self.armed = False
            return "ZOOM_IN"

        # Index + middle slide left -> zoom out.
        if gesture == "ZOOM_OUT" and displacement <= -self.movement_threshold:
            self.armed = False
            return "ZOOM_OUT"

        return None
