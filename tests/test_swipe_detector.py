from src.gestures.swipe_detector import SwipeDetector


OPEN_PALM = [1, 1, 1, 1, 1]       # move hand UP   -> SCROLL_DOWN
FOUR_FINGERS = [0, 1, 1, 1, 1]    # move hand DOWN -> SCROLL_UP
OTHER_POSE = [0, 1, 1, 0, 0]


def make_hand(palm_y, hand_size=100):
    """Hand whose palm centre is at palm_y and whose wrist->MCP length is hand_size."""
    landmarks = [[0, 0, 0] for _ in range(21)]
    landmarks[0] = [200, palm_y + hand_size / 2, 0]   # wrist
    landmarks[9] = [200, palm_y - hand_size / 2, 0]   # middle MCP
    return {"lm_list": landmarks}


def test_first_position_does_not_scroll():
    detector = SwipeDetector()
    assert detector.update(make_hand(200), OPEN_PALM) is None


def test_open_palm_moving_up_scrolls_down():
    detector = SwipeDetector()
    detector.update(make_hand(200), OPEN_PALM)
    assert detector.update(make_hand(140), OPEN_PALM) == "SCROLL_DOWN"


def test_four_fingers_moving_down_scrolls_up():
    detector = SwipeDetector()
    detector.update(make_hand(100), FOUR_FINGERS)
    assert detector.update(make_hand(160), FOUR_FINGERS) == "SCROLL_UP"


def test_wrong_direction_does_not_scroll():
    detector = SwipeDetector()
    detector.update(make_hand(200), OPEN_PALM)
    assert detector.update(make_hand(260), OPEN_PALM) is None


def test_small_movement_does_not_scroll():
    detector = SwipeDetector()
    detector.update(make_hand(200), OPEN_PALM)
    assert detector.update(make_hand(180), OPEN_PALM) is None


def test_threshold_scales_with_hand_size():
    # Same 50 px movement: enough for a small (far-away) hand ...
    far = SwipeDetector()
    far.update(make_hand(200, hand_size=60), OPEN_PALM)
    assert far.update(make_hand(150, hand_size=60), OPEN_PALM) == "SCROLL_DOWN"

    # ... but not for a large (close-up) hand.
    near = SwipeDetector()
    near.update(make_hand(200, hand_size=160), OPEN_PALM)
    assert near.update(make_hand(150, hand_size=160), OPEN_PALM) is None


def test_one_stroke_triggers_only_once():
    detector = SwipeDetector()
    detector.update(make_hand(200), OPEN_PALM)

    assert detector.update(make_hand(140), OPEN_PALM) == "SCROLL_DOWN"
    assert detector.update(make_hand(100), OPEN_PALM) is None
    assert detector.update(make_hand(80), OPEN_PALM) is None


def test_returning_to_start_rearms_detector():
    detector = SwipeDetector()
    detector.update(make_hand(200), OPEN_PALM)

    assert detector.update(make_hand(140), OPEN_PALM) == "SCROLL_DOWN"
    assert detector.update(make_hand(200), OPEN_PALM) is None
    assert detector.update(make_hand(205), OPEN_PALM) is None  # rearmed here
    assert detector.update(make_hand(140), OPEN_PALM) == "SCROLL_DOWN"


def test_brief_pose_failure_does_not_reset_detector():
    detector = SwipeDetector()
    detector.update(make_hand(200), OPEN_PALM)

    assert detector.update(make_hand(180), OTHER_POSE) is None
    assert detector.update(make_hand(140), OPEN_PALM) == "SCROLL_DOWN"


def test_sustained_pose_failure_resets_detector():
    detector = SwipeDetector()
    detector.update(make_hand(200), OPEN_PALM)

    for _ in range(3):
        assert detector.update(make_hand(180), OTHER_POSE) is None

    # Fresh position is needed after reset.
    assert detector.update(make_hand(140), OPEN_PALM) is None


def test_missing_hand_resets():
    detector = SwipeDetector()
    detector.update(make_hand(200), OPEN_PALM)
    assert detector.update(None, OPEN_PALM) is None
    assert detector.anchor_y is None
