from src.gestures.pinky_detector import PinkyDetector


def make_hand():
    landmarks = [[0, 0, 0] for _ in range(21)]
    return {"lm_list": landmarks}


PINKY_UP = [0, 0, 0, 0, 1]
PINKY_UP_THUMB_OUT = [1, 0, 0, 0, 1]
FIST = [0, 0, 0, 0, 0]


def feed(detector, finger_states, frames):
    """Send the same pose for several frames and collect the results."""
    return [detector.update(make_hand(), finger_states) for _ in range(frames)]


def test_single_frame_does_not_click():
    detector = PinkyDetector()
    assert detector.update(make_hand(), PINKY_UP) is None


def test_held_pose_triggers_right_click():
    detector = PinkyDetector(hold_frames=5)
    results = feed(detector, PINKY_UP, 5)

    assert results[:4] == [None] * 4
    assert results[4] == "RIGHT_CLICK"


def test_holding_pose_triggers_only_once():
    detector = PinkyDetector(hold_frames=5)
    results = feed(detector, PINKY_UP, 30)

    assert results.count("RIGHT_CLICK") == 1


def test_release_rearms_detector():
    detector = PinkyDetector(hold_frames=5, release_frames=3)
    feed(detector, PINKY_UP, 5)
    feed(detector, FIST, 3)

    results = feed(detector, PINKY_UP, 5)
    assert results[4] == "RIGHT_CLICK"


def test_brief_release_does_not_rearm():
    detector = PinkyDetector(hold_frames=5, release_frames=3)
    feed(detector, PINKY_UP, 5)

    # One glitchy frame while still holding the pinky up.
    feed(detector, FIST, 1)
    results = feed(detector, PINKY_UP, 10)

    assert "RIGHT_CLICK" not in results


def test_thumb_out_does_not_click():
    detector = PinkyDetector()
    results = feed(detector, PINKY_UP_THUMB_OUT, 20)

    assert "RIGHT_CLICK" not in results


def test_fist_does_not_click():
    detector = PinkyDetector()
    results = feed(detector, FIST, 20)

    assert "RIGHT_CLICK" not in results


def test_flicker_during_fist_does_not_click():
    detector = PinkyDetector(hold_frames=5)
    results = []

    # Pinky flickers up for 2 frames at a time during a fist.
    for _ in range(5):
        results += feed(detector, FIST, 1)
        results += feed(detector, PINKY_UP, 2)

    assert "RIGHT_CLICK" not in results


def test_no_hand_resets_progress():
    detector = PinkyDetector(hold_frames=5)
    feed(detector, PINKY_UP, 4)

    assert detector.update(None, None) is None

    results = feed(detector, PINKY_UP, 5)
    assert results[:4] == [None] * 4
    assert results[4] == "RIGHT_CLICK"