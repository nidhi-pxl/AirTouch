from src.gestures.thumbs_down_detector import ThumbsDownDetector


def make_hand(thumb_dx, thumb_dy):
    """Build a hand with scale 100 and the thumb tip offset from the thumb MCP."""
    landmarks = [[0, 0, 0] for _ in range(21)]
    landmarks[0] = [100, 300, 0]   # wrist
    landmarks[9] = [100, 200, 0]   # middle MCP -> hand scale = 100
    landmarks[2] = [150, 200, 0]   # thumb MCP
    landmarks[4] = [150 + thumb_dx, 200 + thumb_dy, 0]  # thumb tip
    return {"lm_list": landmarks}


THUMB_ONLY = [1, 0, 0, 0, 0]
FIST = [0, 0, 0, 0, 0]

THUMB_DOWN = make_hand(0, 50)
THUMB_UP = make_hand(0, -50)
THUMB_RIGHT = make_hand(50, 0)
THUMB_LEFT = make_hand(-50, 0)
THUMB_DOWN_TILTED = make_hand(20, 50)
THUMB_SLIGHTLY_DOWN = make_hand(0, 10)


def feed(detector, hand, finger_states, frames):
    """Send the same hand and pose for several frames and collect the results."""
    return [detector.update(hand, finger_states) for _ in range(frames)]


def test_single_frame_does_not_undo():
    detector = ThumbsDownDetector()
    assert detector.update(THUMB_DOWN, THUMB_ONLY) is None


def test_held_thumbs_down_triggers_undo():
    detector = ThumbsDownDetector(hold_frames=5)
    results = feed(detector, THUMB_DOWN, THUMB_ONLY, 5)

    assert results[:4] == [None] * 4
    assert results[4] == "UNDO"


def test_holding_pose_triggers_only_once():
    detector = ThumbsDownDetector(hold_frames=5)
    results = feed(detector, THUMB_DOWN, THUMB_ONLY, 30)

    assert results.count("UNDO") == 1


def test_release_rearms_detector():
    detector = ThumbsDownDetector(hold_frames=5, release_frames=3)
    feed(detector, THUMB_DOWN, THUMB_ONLY, 5)
    feed(detector, THUMB_DOWN, FIST, 3)

    results = feed(detector, THUMB_DOWN, THUMB_ONLY, 5)
    assert results[4] == "UNDO"


def test_brief_release_does_not_rearm():
    detector = ThumbsDownDetector(hold_frames=5, release_frames=3)
    feed(detector, THUMB_DOWN, THUMB_ONLY, 5)

    feed(detector, THUMB_DOWN, FIST, 1)
    results = feed(detector, THUMB_DOWN, THUMB_ONLY, 10)

    assert "UNDO" not in results


def test_thumbs_up_does_not_undo():
    detector = ThumbsDownDetector()
    assert "UNDO" not in feed(detector, THUMB_UP, THUMB_ONLY, 20)


def test_sideways_thumb_does_not_undo():
    detector = ThumbsDownDetector()
    assert "UNDO" not in feed(detector, THUMB_RIGHT, THUMB_ONLY, 20)

    detector = ThumbsDownDetector()
    assert "UNDO" not in feed(detector, THUMB_LEFT, THUMB_ONLY, 20)


def test_tilted_thumbs_down_still_undoes():
    detector = ThumbsDownDetector()
    assert "UNDO" in feed(detector, THUMB_DOWN_TILTED, THUMB_ONLY, 5)


def test_small_downward_wobble_does_not_undo():
    detector = ThumbsDownDetector()
    assert "UNDO" not in feed(detector, THUMB_SLIGHTLY_DOWN, THUMB_ONLY, 20)


def test_wrong_finger_states_do_not_undo():
    detector = ThumbsDownDetector()
    assert "UNDO" not in feed(detector, THUMB_DOWN, FIST, 20)


def test_no_hand_resets_progress():
    detector = ThumbsDownDetector(hold_frames=5)
    feed(detector, THUMB_DOWN, THUMB_ONLY, 4)

    assert detector.update(None, None) is None

    results = feed(detector, THUMB_DOWN, THUMB_ONLY, 5)
    assert results[:4] == [None] * 4
    assert results[4] == "UNDO"


def test_missing_landmarks_do_not_crash():
    detector = ThumbsDownDetector()
    assert detector.update({}, THUMB_ONLY) is None