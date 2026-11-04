"""Detect the thumbs-down pose used for undo."""

import math


class ThumbsDownDetector:
    """Fire UNDO once when a thumbs-down pose is held."""

    # [Thumb, Index, Middle, Ring, Pinky]
    POSE_TEMPLATE = [1, 0, 0, 0, 0]

    def __init__(
        self,
        hold_frames: int = 5,
        release_frames: int = 3,
        min_down_ratio: float = 0.25,
    ):
        self.hold_frames = hold_frames
        self.release_frames = release_frames
        self.min_down_ratio = min_down_ratio

        self.hold_count = 0
        self.release_count = 0
        self.armed = True

    def reset(self):
        """Reset pose tracking."""
        self.hold_count = 0
        self.release_count = 0
        self.armed = True

    def _matches_fingers(self, finger_states: list[int] | None) -> bool:
        if finger_states is None or len(finger_states) != 5:
            return False

        return all(
            expected is None or expected == actual
            for expected, actual in zip(self.POSE_TEMPLATE, finger_states)
        )

    def _thumb_points_down(self, hand_info: dict) -> bool:
        lm_list = hand_info.get("lm_list")
        if lm_list is None or len(lm_list) < 21:
            return False

        # Hand scale: wrist (0) to middle finger MCP (9).
        hand_scale = math.hypot(
            lm_list[9][0] - lm_list[0][0],
            lm_list[9][1] - lm_list[0][1],
        )
        if hand_scale == 0:
            return False

        # Thumb vector: thumb MCP (2) to thumb tip (4).
        dx = lm_list[4][0] - lm_list[2][0]
        dy = lm_list[4][1] - lm_list[2][1]  # positive = pointing down

        points_mostly_down = dy > abs(dx)
        far_enough_down = dy / hand_scale > self.min_down_ratio

        return points_mostly_down and far_enough_down

    def _matches_pose(self, hand_info: dict, finger_states: list[int] | None) -> bool:
        return self._matches_fingers(finger_states) and self._thumb_points_down(hand_info)

    def update(
        self,
        hand_info: dict | None,
        finger_states: list[int] | None,
    ) -> str | None:
        """Return UNDO or None."""

        if hand_info is None:
            self.reset()
            return None

        if self._matches_pose(hand_info, finger_states):
            self.release_count = 0

            if not self.armed:
                return None

            self.hold_count += 1

            # Pose held long enough: fire once and disarm.
            if self.hold_count >= self.hold_frames:
                self.armed = False
                self.hold_count = 0
                return "UNDO"

            return None

        # Pose not present.
        self.hold_count = 0
        self.release_count += 1

        # Re-arm only after the pose has been gone for a few frames.
        if self.release_count >= self.release_frames:
            self.armed = True

        return None