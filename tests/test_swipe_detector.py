
from src.gestures.swipe_detector import SwipeDetector


def make_hand(index_y):
    landmarks = [[0, 0, 0] for _ in range(21)]
    landmarks[8] = [100, index_y, 0]
    return {"lm_list": landmarks}


POINTING = [0, 1, 0, 0, 0]


def test_first_position_does_not_scroll():
    detector = SwipeDetector()
    assert detector.update(make_hand(200), POINTING) is None


def test_upward_movement_scrolls_up():
    detector = SwipeDetector()
    detector.update(make_hand(200), POINTING)
    assert detector.update(make_hand(140), POINTING) == "SCROLL_UP"


def test_downward_movement_scrolls_down():
    detector = SwipeDetector()
    detector.update(make_hand(100), POINTING)
    assert detector.update(make_hand(160), POINTING) == "SCROLL_DOWN"


def test_small_movement_does_not_scroll():
    detector = SwipeDetector()
    detector.update(make_hand(200), POINTING)
    assert detector.update(make_hand(180), POINTING) is None


def test_one_stroke_triggers_only_once():
    detector = SwipeDetector()
    detector.update(make_hand(200), POINTING)

    assert detector.update(make_hand(140), POINTING) == "SCROLL_UP"
    assert detector.update(make_hand(100), POINTING) is None
    assert detector.update(make_hand(80), POINTING) is None


def test_returning_to_start_rearms_detector():
    detector = SwipeDetector()
    detector.update(make_hand(200), POINTING)

    assert detector.update(make_hand(140), POINTING) == "SCROLL_UP"
    assert detector.update(make_hand(200), POINTING) is None
    assert detector.update(make_hand(260), POINTING) == "SCROLL_DOWN"


def test_brief_pose_failure_does_not_reset_detector():
    detector = SwipeDetector()
    detector.update(make_hand(200), POINTING)

    assert detector.update(make_hand(180), [0, 1, 1, 0, 0]) is None
    assert detector.update(make_hand(140), POINTING) == "SCROLL_UP"


def test_sustained_pose_failure_resets_detector():
    detector = SwipeDetector()
    detector.update(make_hand(200), POINTING)

    for _ in range(3):
        assert detector.update(make_hand(180), [0, 1, 1, 0, 0]) is None

    # Fresh position is needed after reset.
    assert detector.update(make_hand(140), POINTING) is None
