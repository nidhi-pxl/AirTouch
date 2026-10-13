
from src.gestures.pinch_detector import PinchDetector


def make_hand(ratio):
    """Create synthetic landmarks with a controllable thumb-index distance."""
    landmarks = [[0, 0, 0] for _ in range(21)]

    # Keep wrist-to-middle-MCP distance at 100 pixels.
    landmarks[0] = [100, 200, 0]
    landmarks[9] = [100, 100, 0]

    # Set thumb and index tips to produce the desired normalized ratio.
    landmarks[4] = [100, 100, 0]
    landmarks[8] = [100 + ratio * 100, 100, 0]

    return {"lm_list": landmarks}


def test_neutral_position_arms_detector():
    detector = PinchDetector()

    assert detector.update(make_hand(0.5)) is None
    assert detector.armed is True


def test_closing_fingers_triggers_zoom_in_once():
    detector = PinchDetector()
    detector.update(make_hand(0.5))

    assert detector.update(make_hand(0.2)) == "ZOOM_IN"
    assert detector.update(make_hand(0.2)) is None


def test_opening_fingers_triggers_zoom_out_once():
    detector = PinchDetector()
    detector.update(make_hand(0.5))

    assert detector.update(make_hand(0.8)) == "ZOOM_OUT"
    assert detector.update(make_hand(0.8)) is None


def test_neutral_position_allows_next_gesture():
    detector = PinchDetector()
    detector.update(make_hand(0.5))

    assert detector.update(make_hand(0.2)) == "ZOOM_IN"
    assert detector.update(make_hand(0.5)) is None
    assert detector.update(make_hand(0.8)) == "ZOOM_OUT"


def test_missing_hand_does_not_trigger_zoom():
    detector = PinchDetector()

    assert detector.update(None) is None


def test_invalid_hand_landmarks_do_not_trigger_zoom():
    detector = PinchDetector()

    assert detector.update({"lm_list": []}) is None