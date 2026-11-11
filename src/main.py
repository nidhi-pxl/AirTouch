
"""AirTouch: mouse control and integrated hand gestures."""

import cv2
import pyautogui
import math
import time

from collections import deque
from statistics import median

from src.vision.hand_tracker import HandTracker

from src.gestures.swipe_detector import SwipeDetector
from src.gestures.pinch_detector import PinchDetector
from src.gestures.pinky_detector import PinkyDetector
from src.gestures.thumbs_down_detector import ThumbsDownDetector

from src.interaction.action_mapper import ActionMapper


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


pyautogui.FAILSAFE = True


# --------------------------------------------------
# MOUSE GESTURE DETECTION
# --------------------------------------------------

def detect_mouse_gesture(hand, finger_states):
    """
    Mouse gesture:
    Thumb closed, index open, middle/ring/pinky closed.

    Exact pattern: [0, 1, 0, 0, 0]
    """

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
    """
    Estimate index finger bend angle.

    5 = index MCP
    6 = index PIP
    8 = index fingertip
    """

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
    """
    Left-click pose:
    Thumb open, index bent, middle/ring/pinky open.
    """

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
# MAIN APPLICATION
# --------------------------------------------------

def main():

    tracker = HandTracker(max_num_hands=1)
    camera = cv2.VideoCapture(0)

    # Friend's gesture detectors.
    scroll_detector = SwipeDetector(movement_threshold=50)
    pinch_detector = PinchDetector()
    pinky_detector = PinkyDetector()
    thumbs_down_detector = ThumbsDownDetector()

    action_mapper = ActionMapper(dry_run=False)

    screen_width, screen_height = pyautogui.size()

    # Mouse state.
    mouse_active = False
    positive_frames = 0
    negative_frames = 0

    # Left-click state.
    left_click_frames = 0
    left_click_armed = False
    left_click_detected = False
    last_left_click_time = 0.0

    # Cursor smoothing.
    x_history = deque(maxlen=FILTER_FRAMES)
    y_history = deque(maxlen=FILTER_FRAMES)

    # Relative cursor anchors.
    hand_anchor_x = None
    hand_anchor_y = None
    screen_anchor_x = None
    screen_anchor_y = None

    last_cursor_x = None
    last_cursor_y = None

    # Camera check.
    if not camera.isOpened():
        print("Error: Could not open webcam.")
        tracker.hands.close()
        return

    print("-----------------------------------")
    print("AirTouch started. Press Q to quit.")
    print("-----------------------------------")
    print("Mouse: Thumb closed, index open, other fingers closed.")
    print("Left-click: Open palm, then bend index finger.")
    print("Right-click: Friend's detector.")
    print("Zoom: Friend's detector.")
    print("Undo: Friend's detector.")
    print("Scroll: Friend's detector.")
    print("-----------------------------------")

    try:

        while True:

            success, frame = camera.read()

            if not success:
                print("Warning: Could not read webcam frame.")
                break

            frame = cv2.flip(frame, 1)

            frame_height, frame_width = frame.shape[:2]

            # Process hand tracking.
            tracker.process_frame(frame)

            hands = tracker.get_hands_info(frame)

            tracker.draw_landmarks(frame)

            if hands:

                hand = hands[0]

                finger_states = tracker.get_finger_states(hand)

                # ----------------------------------
                # FRIEND'S GESTURE DETECTORS
                # DO NOT MODIFY THEIR IMPLEMENTATIONS
                # ----------------------------------

                scroll_event = scroll_detector.update(
                    hand,
                    finger_states,
                )
                action_mapper.handle_event(scroll_event)

                zoom_event = pinch_detector.update(hand, finger_states)                
                action_mapper.handle_event(zoom_event)

                right_click_event = pinky_detector.update(
                    hand,
                    finger_states,
                )
                action_mapper.handle_event(right_click_event)

                undo_event = thumbs_down_detector.update(
                    hand,
                    finger_states,
                )
                action_mapper.handle_event(undo_event)

                # ----------------------------------
                # YOUR MOUSE AND LEFT-CLICK DETECTORS
                # ----------------------------------

                mouse_gesture = detect_mouse_gesture(
                    hand,
                    finger_states,
                )

                left_click_pose, index_angle = (
                    detect_left_click_gesture(
                        hand,
                        finger_states,
                    )
                )

                open_palm = is_open_palm(finger_states)

                # ----------------------------------
                # LEFT-CLICK ARMING
                # ----------------------------------

                # An open palm is required before every click.
                if open_palm:
                    left_click_armed = True
                    left_click_frames = 0

                # Count consecutive valid click-pose frames.
                if left_click_armed and left_click_pose:
                    left_click_frames += 1
                else:
                    left_click_frames = 0

                left_click_detected = (
                    left_click_armed
                    and left_click_frames >= LEFT_CLICK_CONFIRM_FRAMES
                )

                # Execute exactly one click.
                now = time.monotonic()

                if (
                    left_click_detected
                    and now - last_left_click_time >= LEFT_CLICK_COOLDOWN
                ):

                    pyautogui.click(button="left")

                    last_left_click_time = now

                    # Disarm until another open palm is detected.
                    left_click_armed = False
                    left_click_frames = 0

                    print("Executed: LEFT_CLICK")

                # ----------------------------------
                # MOUSE ACTIVATION / DEACTIVATION
                # ----------------------------------

                # Pause mouse movement during the click pose.
                if left_click_pose:

                    mouse_active = False

                    positive_frames = 0
                    negative_frames = 0

                    (
                        hand_anchor_x,
                        hand_anchor_y,
                        screen_anchor_x,
                        screen_anchor_y,
                        last_cursor_x,
                        last_cursor_y,
                    ) = reset_cursor_anchors()

                    x_history.clear()
                    y_history.clear()

                else:

                    if mouse_gesture:
                        positive_frames += 1
                        negative_frames = 0

                    else:
                        negative_frames += 1
                        positive_frames = 0

                    # Activate mouse mode.
                    if (
                        positive_frames >= ACTIVATION_FRAMES
                        and not mouse_active
                    ):

                        fingertip = get_index_tip(hand)

                        if fingertip is not None:

                            mouse_active = True

                            hand_anchor_x, hand_anchor_y = fingertip

                            (
                                screen_anchor_x,
                                screen_anchor_y,
                            ) = pyautogui.position()

                            x_history.clear()
                            y_history.clear()

                            last_cursor_x = screen_anchor_x
                            last_cursor_y = screen_anchor_y

                    # Deactivate mouse mode.
                    if (
                        negative_frames >= DEACTIVATION_FRAMES
                        and mouse_active
                    ):

                        mouse_active = False

                        (
                            hand_anchor_x,
                            hand_anchor_y,
                            screen_anchor_x,
                            screen_anchor_y,
                            last_cursor_x,
                            last_cursor_y,
                        ) = reset_cursor_anchors()

                        x_history.clear()
                        y_history.clear()

                    # ----------------------------------
                    # RELATIVE CURSOR MOVEMENT
                    # ----------------------------------

                    if mouse_active:

                        fingertip = get_index_tip(hand)

                        if fingertip is not None:

                            raw_x, raw_y = fingertip

                            x_history.append(raw_x)
                            y_history.append(raw_y)

                            if len(x_history) == FILTER_FRAMES:

                                filtered_x = median(x_history)
                                filtered_y = median(y_history)

                                delta_x = (
                                    filtered_x - hand_anchor_x
                                )

                                delta_y = (
                                    filtered_y - hand_anchor_y
                                )

                                target_x = int(
                                    screen_anchor_x
                                    + delta_x
                                    * screen_width
                                    / frame_width
                                    * CURSOR_SENSITIVITY
                                )

                                target_y = int(
                                    screen_anchor_y
                                    + delta_y
                                    * screen_height
                                    / frame_height
                                    * CURSOR_SENSITIVITY
                                )

                                target_x = max(
                                    0,
                                    min(screen_width - 1, target_x),
                                )

                                target_y = max(
                                    0,
                                    min(screen_height - 1, target_y),
                                )

                                dx = target_x - last_cursor_x
                                dy = target_y - last_cursor_y

                                if (
                                    abs(dx) > DEAD_ZONE
                                    or abs(dy) > DEAD_ZONE
                                ):

                                    pyautogui.moveTo(
                                        target_x,
                                        target_y,
                                        duration=0,
                                    )

                                    last_cursor_x = target_x
                                    last_cursor_y = target_y

                # ----------------------------------
                # CAMERA DISPLAY
                # ----------------------------------

                cv2.putText(
                    frame,
                    f"Finger states: {finger_states}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 0),
                    2,
                )

                mouse_status = (
                    "MOUSE ACTIVE"
                    if mouse_active
                    else "MOUSE INACTIVE"
                )

                mouse_color = (
                    (0, 255, 0)
                    if mouse_active
                    else (0, 0, 255)
                )

                cv2.putText(
                    frame,
                    mouse_status,
                    (10, 65),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    mouse_color,
                    2,
                )

                if index_angle is not None:
                    angle_text = (
                        f"Index bend angle: {index_angle:.1f}"
                    )
                else:
                    angle_text = "Index bend angle: unavailable"

                cv2.putText(
                    frame,
                    angle_text,
                    (10, 100),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )

                if left_click_detected:
                    click_status = "LEFT CLICK EXECUTED"
                    click_color = (0, 255, 0)

                elif left_click_armed and left_click_pose:
                    click_status = (
                        f"Confirming click: "
                        f"{left_click_frames}/"
                        f"{LEFT_CLICK_CONFIRM_FRAMES}"
                    )
                    click_color = (0, 165, 255)

                elif left_click_armed:
                    click_status = "CLICK ARMED - OPEN PALM DETECTED"
                    click_color = (255, 255, 0)

                else:
                    click_status = "SHOW OPEN PALM TO ARM CLICK"
                    click_color = (0, 0, 255)

                cv2.putText(
                    frame,
                    click_status,
                    (10, 135),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    click_color,
                    2,
                )

                cv2.putText(
                    frame,
                    f"Hand: {hand['type']} | "
                    f"Confidence: {hand['score']:.2f}",
                    (10, 170),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                )

            # ----------------------------------
            # NO HAND DETECTED
            # ----------------------------------

            else:

                positive_frames = 0
                negative_frames += 1
                scroll_detector.reset()

                left_click_frames = 0
                left_click_armed = False
                left_click_detected = False

                # Reset friend's gesture detectors.
                pinch_detector.reset()
                pinky_detector.reset()
                thumbs_down_detector.reset()

                # Deactivate mouse.
                if negative_frames >= DEACTIVATION_FRAMES:

                    mouse_active = False

                    (
                        hand_anchor_x,
                        hand_anchor_y,
                        screen_anchor_x,
                        screen_anchor_y,
                        last_cursor_x,
                        last_cursor_y,
                    ) = reset_cursor_anchors()

                    x_history.clear()
                    y_history.clear()

                cv2.putText(
                    frame,
                    "No hand detected",
                    (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 0, 255),
                    2,
                )

                cv2.putText(
                    frame,
                    "MOUSE INACTIVE",
                    (10, 65),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                )

                cv2.putText(
                    frame,
                    "SHOW OPEN PALM TO ARM CLICK",
                    (10, 135),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 0, 255),
                    2,
                )

            # Show camera feed.
            cv2.imshow(
                "AirTouch - Hand Tracking",
                frame,
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except pyautogui.FailSafeException:

        print("Mouse control stopped by PyAutoGUI fail-safe.")

    finally:

        camera.release()
        cv2.destroyAllWindows()
        tracker.hands.close()

        print("AirTouch stopped.")


if __name__ == "__main__":
    main()
