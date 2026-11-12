from src.gestures.zoom_detector import ZoomDetector

IN_POSE = [1, 0, 0, 0, 0]
OUT_POSE = [0, 1, 1, 0, 0]
FIST = [0, 0, 0, 0, 0]


def make_hand(thumb_x=100, fingers_x=100, thumb_dy=0):
    """Synthetic hand with hand scale = 100 px (wrist to middle MCP)."""
    lm = [[0, 0, 0] for _ in range(21)]
    lm[0] = [100, 200, 0]
    lm[9] = [100, 100, 0]
    lm[2] = [100, 150, 0]                   # thumb MCP
    lm[4] = [thumb_x, 150 + thumb_dy, 0]    # thumb tip
    lm[8] = [fingers_x, 50, 0]              # index tip
    lm[12] = [fingers_x, 50, 0]             # middle tip
    return {"lm_list": lm}


def test_thumb_slide_right_zooms_in_once():
    d = ZoomDetector()
    assert d.update(make_hand(thumb_x=100), IN_POSE) is None
    assert d.update(make_hand(thumb_x=130), IN_POSE) is None  # too small
    assert d.update(make_hand(thumb_x=170), IN_POSE) == "ZOOM_IN"
    assert d.update(make_hand(thumb_x=200), IN_POSE) is None  # no repeat


def test_thumb_slide_left_does_nothing():
    d = ZoomDetector()
    d.update(make_hand(thumb_x=100), IN_POSE)
    assert d.update(make_hand(thumb_x=20), IN_POSE) is None


def test_two_fingers_slide_left_zooms_out_once():
    d = ZoomDetector()
    assert d.update(make_hand(fingers_x=100), OUT_POSE) is None
    assert d.update(make_hand(fingers_x=70), OUT_POSE) is None
    assert d.update(make_hand(fingers_x=30), OUT_POSE) == "ZOOM_OUT"
    assert d.update(make_hand(fingers_x=0), OUT_POSE) is None


def test_two_fingers_slide_right_does_nothing():
    d = ZoomDetector()
    d.update(make_hand(fingers_x=100), OUT_POSE)
    assert d.update(make_hand(fingers_x=200), OUT_POSE) is None


def test_rearms_after_returning_to_start():
    d = ZoomDetector()
    d.update(make_hand(thumb_x=100), IN_POSE)
    assert d.update(make_hand(thumb_x=170), IN_POSE) == "ZOOM_IN"
    assert d.update(make_hand(thumb_x=105), IN_POSE) is None  # rearm
    assert d.update(make_hand(thumb_x=175), IN_POSE) == "ZOOM_IN"


def test_thumb_pointing_down_is_not_zoom():
    d = ZoomDetector()
    d.update(make_hand(thumb_x=100, thumb_dy=60), IN_POSE)
    assert d.update(make_hand(thumb_x=170, thumb_dy=60), IN_POSE) is None


def test_wrong_pose_does_nothing():
    d = ZoomDetector()
    d.update(make_hand(thumb_x=100), FIST)
    assert d.update(make_hand(thumb_x=200), FIST) is None


def test_changing_pose_restarts_tracking():
    d = ZoomDetector()
    d.update(make_hand(thumb_x=100, fingers_x=100), IN_POSE)
    # Switching pose must not fire from the old anchor.
    assert d.update(make_hand(thumb_x=100, fingers_x=0), OUT_POSE) is None


def test_missing_hand_resets():
    d = ZoomDetector()
    d.update(make_hand(thumb_x=100), IN_POSE)
    assert d.update(None, None) is None
    assert d.active_gesture is None


def test_invalid_landmarks_do_not_trigger():
    d = ZoomDetector()
    assert d.update({"lm_list": []}, IN_POSE) is None
