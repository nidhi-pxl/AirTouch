
from src.gestures.swipe_detector import SwipeDetector


def make_hand(index_y):
    landmarks = [[0, 0, 0] for _ in range(21)]
    landmarks[8] = [100, index_y, 0]

    return {"lm_list": landmarks}


POINTING = [0, 1, 0, 0, 0]


def test_first_position_does_not_scroll():
    detector = SwipeDetector(movement_threshold=50)

    assert detector.update(make_hand(200), POINTING) is None


def test_upward_movement_scrolls_up():
    detector = SwipeDetector(movement_threshold=50)

    detector.update(make_hand(200), POINTING)

    assert detector.update(make_hand(140), POINTING) == "SCROLL_UP"


def test_downward_movement_scrolls_down():
    detector = SwipeDetector(movement_threshold=50)

    detector.update(make_hand(100), POINTING)

    assert detector.update(make_hand(160), POINTING) == "SCROLL_DOWN"


def test_small_movement_does_not_scroll():
    detector = SwipeDetector(movement_threshold=50)

    detector.update(make_hand(200), POINTING)

    assert detector.update(make_hand(180), POINTING) is None


def test_non_pointing_pose_resets_detector():
    detector = SwipeDetector(movement_threshold=50)

    detector.update(make_hand(200), POINTING)

    assert detector.update(make_hand(100), [0, 1, 1, 0, 0]) is None

    # The next pointing frame establishes a fresh reference.
    assert detector.update(make_hand(100), POINTING) is None
