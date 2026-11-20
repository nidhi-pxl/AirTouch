
"""AirTouch: mouse control and integrated hand gestures."""

import math
import sys


# --------------------------------------------------
# MOUSE SETTINGS
# --------------------------------------------------

ACTIVATION_FRAMES = 3
DEACTIVATION_FRAMES = 4

FILTER_FRAMES = 5
DEAD_ZONE = 5
CURSOR_SENSITIVITY = 0.75


# --------------------------------------------------
# LEFT-CLICK SETTINGS
# --------------------------------------------------

LEFT_CLICK_BENT_ANGLE = 145
LEFT_CLICK_CONFIRM_FRAMES = 3
LEFT_CLICK_COOLDOWN = 0.6


# --------------------------------------------------
# MOUSE GESTURE DETECTION
# --------------------------------------------------

def detect_mouse_gesture(hand, finger_states):
    """Detect thumb closed, index open, remaining fingers closed."""
    if hand is None or len(finger_states) != 5:
        return False

    return finger_states == [0, 1, 0, 0, 0]


def get_index_tip(hand):
    """Return index fingertip coordinates in camera pixels."""
    try:
        landmarks = hand["lm_list"]
        return landmarks[8][0], landmarks[8][1]
    except (IndexError, KeyError, TypeError):
        return None


# --------------------------------------------------
# LEFT-CLICK GESTURE DETECTION
# --------------------------------------------------

def calculate_angle(a, b, c):
    """Calculate angle ABC in degrees."""

    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])

    magnitude_ba = math.hypot(*ba)
    magnitude_bc = math.hypot(*bc)

    if magnitude_ba == 0 or magnitude_bc == 0:
        return None

    dot_product = ba[0] * bc[0] + ba[1] * bc[1]
    cosine = dot_product / (magnitude_ba * magnitude_bc)
    cosine = max(-1.0, min(1.0, cosine))

    return math.degrees(math.acos(cosine))


def get_index_bend_angle(hand):
    """Estimate index finger bend angle."""

    try:
        landmarks = hand["lm_list"]

        return calculate_angle(
            landmarks[5],
            landmarks[6],
            landmarks[8],
        )

    except (IndexError, KeyError, TypeError):
        return None


def detect_left_click_gesture(hand, finger_states):
    """Detect the left-click pose."""

    if hand is None or len(finger_states) != 5:
        return False, None

    required_fingers_open = (
        finger_states[0] == 1
        and finger_states[2] == 1
        and finger_states[3] == 1
        and finger_states[4] == 1
    )

    angle = get_index_bend_angle(hand)

    index_is_bent = (
        finger_states[1] == 0
        and angle is not None
        and angle < LEFT_CLICK_BENT_ANGLE
    )

    return required_fingers_open and index_is_bent, angle


def is_open_palm(finger_states):
    """Check whether all five fingers are open."""

    return (
        finger_states is not None
        and len(finger_states) == 5
        and finger_states == [1, 1, 1, 1, 1]
    )


# --------------------------------------------------
# CURSOR RESET
# --------------------------------------------------

def reset_cursor_anchors():
    """Return empty cursor-anchor values."""

    return None, None, None, None, None, None


# --------------------------------------------------
# GUI APPLICATION ENTRY POINT
# --------------------------------------------------

def main():

    # IMPORTANT:
    # Import MainWindow here, not at the top of the file.
    # This avoids the circular import with camera_worker.py.

    from src.gui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("AirTouch")
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())