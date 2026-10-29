
"""AirTouch: index-finger mouse control."""

import cv2
import pyautogui
from collections import deque
from statistics import median

from src.vision.hand_tracker import HandTracker
from src.gestures.swipe_detector import SwipeDetector
from src.interaction.action_mapper import ActionMapper


# Gesture settings
ACTIVATION_FRAMES = 3
DEACTIVATION_FRAMES = 4

# Cursor settings
FILTER_FRAMES = 5
DEAD_ZONE = 5
CURSOR_SENSITIVITY = 0.75

pyautogui.FAILSAFE = True


def detect_mouse_gesture(hand, finger_states):
    """Index raised; middle, ring, and pinky closed."""
    if hand is None or len(finger_states) != 5:
        return False

    return (
        finger_states[1] == 1
        and finger_states[2] == 0
        and finger_states[3] == 0
        and finger_states[4] == 0
    )


def get_index_tip(hand):
    """Return the index fingertip coordinates in camera pixels."""
    try:
        landmarks = hand["lm_list"]
        return landmarks[8][0], landmarks[8][1]
    except (IndexError, KeyError, TypeError):
        return None


def main():
    tracker = HandTracker(max_num_hands=1)
    camera = cv2.VideoCapture(0)

    # Preserve existing swipe integration.
    scroll_detector = SwipeDetector(movement_threshold=50)
    action_mapper = ActionMapper(dry_run=True)

    screen_width, screen_height = pyautogui.size()

    mouse_active = False
    positive_frames = 0
    negative_frames = 0

    # Filter fingertip noise.
    x_history = deque(maxlen=FILTER_FRAMES)
    y_history = deque(maxlen=FILTER_FRAMES)

    # Relative movement anchors.
    hand_anchor_x = None
    hand_anchor_y = None
    screen_anchor_x = None
    screen_anchor_y = None

    last_cursor_x = None
    last_cursor_y = None

    if not camera.isOpened():
        print("Error: Could not open webcam.")
        tracker.hands.close()
        return

    print("AirTouch mouse started. Press Q to quit.")
    print("Raise only your index finger to control the cursor.")

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("Warning: Could not read webcam frame.")
                break

            frame = cv2.flip(frame, 1)
            frame_height, frame_width = frame.shape[:2]

            tracker.process_frame(frame)
            hands = tracker.get_hands_info(frame)
            tracker.draw_landmarks(frame)

            if hands:
                hand = hands[0]
                finger_states = tracker.get_finger_states(hand)

                # Preserve existing swipe handling.
                scroll_event = scroll_detector.update(
                    hand, finger_states
                )
                action_mapper.handle_event(scroll_event)

                detected = detect_mouse_gesture(
                    hand, finger_states
                )

                if detected:
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
                    mouse_active = True

                    # Anchor the hand to the cursor's CURRENT position.
                    # This prevents a jump when mouse mode is reactivated.
                    fingertip = get_index_tip(hand)

                    if fingertip is not None:
                        hand_anchor_x, hand_anchor_y = fingertip
                        screen_anchor_x, screen_anchor_y = (
                            pyautogui.position()
                        )

                        x_history.clear()
                        y_history.clear()

                        last_cursor_x = screen_anchor_x
                        last_cursor_y = screen_anchor_y

                # Deactivate mouse mode without moving the cursor.
                if (
                    negative_frames >= DEACTIVATION_FRAMES
                    and mouse_active
                ):
                    mouse_active = False

                    # Clear anchors so the next activation starts
                    # from the cursor's new, actual screen position.
                    hand_anchor_x = None
                    hand_anchor_y = None
                    screen_anchor_x = None
                    screen_anchor_y = None

                    x_history.clear()
                    y_history.clear()

                    last_cursor_x = None
                    last_cursor_y = None

                if mouse_active:
                    fingertip = get_index_tip(hand)

                    if fingertip is not None:
                        raw_x, raw_y = fingertip

                        x_history.append(raw_x)
                        y_history.append(raw_y)

                        if len(x_history) == FILTER_FRAMES:
                            filtered_x = median(x_history)
                            filtered_y = median(y_history)

                            # Calculate movement relative to the
                            # fingertip position at activation.
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
                                0, min(screen_width - 1, target_x)
                            )
                            target_y = max(
                                0, min(screen_height - 1, target_y)
                            )

                            # Ignore tiny target changes to reduce jitter.
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

                                last_cursor_x, last_cursor_y = (
                                    target_x,
                                    target_y,
                                )

                status = (
                    "MOUSE ACTIVE"
                    if mouse_active
                    else "MOUSE INACTIVE"
                )
                color = (
                    (0, 255, 0)
                    if mouse_active
                    else (0, 0, 255)
                )

                cv2.putText(
                    frame,
                    f"Finger states: {finger_states}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 0),
                    2,
                )

                cv2.putText(
                    frame,
                    status,
                    (10, 65),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    color,
                    2,
                )

            else:
                positive_frames = 0
                negative_frames += 1

                if negative_frames >= DEACTIVATION_FRAMES:
                    mouse_active = False

                    hand_anchor_x = None
                    hand_anchor_y = None
                    screen_anchor_x = None
                    screen_anchor_y = None

                    x_history.clear()
                    y_history.clear()

                    last_cursor_x = None
                    last_cursor_y = None

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

            cv2.imshow("AirTouch - Mouse Control", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except pyautogui.FailSafeException:
        print("Mouse control stopped by the PyAutoGUI fail-safe.")

    finally:
        camera.release()
        cv2.destroyAllWindows()
        tracker.hands.close()
        print("AirTouch mouse stopped.")


if __name__ == "__main__":
    main()
