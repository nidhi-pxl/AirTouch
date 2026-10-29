
"""AirTouch: stable index-finger mouse control."""

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

# Cursor stability settings
FILTER_FRAMES = 5
DEAD_ZONE = 6

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


def get_cursor_position(
    hand,
    frame_width,
    frame_height,
    screen_width,
    screen_height,
):
    """Convert the index fingertip position to screen coordinates."""
    try:
        index_tip = hand["lm_list"][8]
        camera_x = index_tip[0]
        camera_y = index_tip[1]

        screen_x = int(camera_x * screen_width / frame_width)
        screen_y = int(camera_y * screen_height / frame_height)

        screen_x = max(0, min(screen_width - 1, screen_x))
        screen_y = max(0, min(screen_height - 1, screen_y))

        return screen_x, screen_y

    except (IndexError, KeyError, TypeError):
        return None


def main():
    tracker = HandTracker(max_num_hands=1)
    camera = cv2.VideoCapture(0)

    # Keep existing swipe handling unchanged.
    scroll_detector = SwipeDetector(movement_threshold=50)
    action_mapper = ActionMapper(dry_run=True)

    screen_width, screen_height = pyautogui.size()

    mouse_active = False
    positive_frames = 0
    negative_frames = 0

    # Median filtering removes sudden fingertip-coordinate jumps.
    x_history = deque(maxlen=FILTER_FRAMES)
    y_history = deque(maxlen=FILTER_FRAMES)

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

                # Preserve the existing swipe detector integration.
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

                if positive_frames >= ACTIVATION_FRAMES:
                    if not mouse_active:
                        # Start fresh when mouse mode activates.
                        x_history.clear()
                        y_history.clear()
                        last_cursor_x = None
                        last_cursor_y = None

                    mouse_active = True

                if negative_frames >= DEACTIVATION_FRAMES:
                    mouse_active = False
                    x_history.clear()
                    y_history.clear()
                    last_cursor_x = None
                    last_cursor_y = None

                if mouse_active:
                    position = get_cursor_position(
                        hand,
                        frame_width,
                        frame_height,
                        screen_width,
                        screen_height,
                    )

                    if position is not None:
                        raw_x, raw_y = position

                        x_history.append(raw_x)
                        y_history.append(raw_y)

                        # Wait for enough samples to stabilize tracking.
                        if len(x_history) == FILTER_FRAMES:
                            target_x = int(median(x_history))
                            target_y = int(median(y_history))

                            if (
                                last_cursor_x is None
                                or last_cursor_y is None
                            ):
                                last_cursor_x = target_x
                                last_cursor_y = target_y

                                pyautogui.moveTo(
                                    target_x, target_y, duration=0
                                )

                            else:
                                dx = target_x - last_cursor_x
                                dy = target_y - last_cursor_y

                                # Ignore tiny coordinate changes.
                                if (
                                    abs(dx) > DEAD_ZONE
                                    or abs(dy) > DEAD_ZONE
                                ):
                                    # Move directly to the filtered target.
                                    # No trailing interpolation or momentum.
                                    pyautogui.moveTo(
                                        target_x, target_y, duration=0
                                    )
                                    last_cursor_x = target_x
                                    last_cursor_y = target_y

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
                    0.6,
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
                    x_history.clear()
                    y_history.clear()
                    last_cursor_x = None
                    last_cursor_y = None

                cv2.putText(
                    frame,
                    "No hand detected",
                    (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
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
