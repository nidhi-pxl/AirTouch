"""Detect the pinky-lift pose used for right click."""


class PinkyDetector:
    """Fire RIGHT_CLICK once when only the pinky is lifted and held."""

    # [Thumb, Index, Middle, Ring, Pinky]; None means "don't care".
    POSE_TEMPLATE = [0, 0, 0, 0, 1]

    def __init__(self, hold_frames: int = 5, release_frames: int = 3):
        self.hold_frames = hold_frames
        self.release_frames = release_frames

        self.hold_count = 0
        self.release_count = 0
        self.armed = True

    def reset(self):
        """Reset pose tracking."""
        self.hold_count = 0
        self.release_count = 0
        self.armed = True

    def _matches_pose(self, finger_states: list[int] | None) -> bool:
        if finger_states is None or len(finger_states) != 5:
            return False

        return all(
            expected is None or expected == actual
            for expected, actual in zip(self.POSE_TEMPLATE, finger_states)
        )

    def update(
        self,
        hand_info: dict | None,
        finger_states: list[int] | None,
    ) -> str | None:
        """Return RIGHT_CLICK or None."""

        if hand_info is None:
            self.reset()
            return None

        if self._matches_pose(finger_states):
            self.release_count = 0

            if not self.armed:
                return None

            self.hold_count += 1

            # Pose held long enough: fire once and disarm.
            if self.hold_count >= self.hold_frames:
                self.armed = False
                self.hold_count = 0
                return "RIGHT_CLICK"

            return None

        # Pose not present.
        self.hold_count = 0
        self.release_count += 1

        # Re-arm only after the pose has been gone for a few frames.
        if self.release_count >= self.release_frames:
            self.armed = True

        return None