
"""AirTouch application entry point.

Current version: webcam and hand-tracking baseline.
Pinch/scroll detection and desktop actions will be integrated
when the gesture and interaction modules are ready.
"""

import cv2

from src.vision.hand_tracker import HandTracker


def main():
    tracker = HandTracker(max_num_hands=1)
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Error: Could not open webcam.")
        tracker.hands.close()
        return

    print("AirTouch started. Press Q to quit.")

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("Warning: Could not read webcam frame.")
                break

            # Mirror the image for a natural webcam interaction.
            frame = cv2.flip(frame, 1)

            # Detect hands and extract their landmarks.
            tracker.process_frame(frame)
            hands = tracker.get_hands_info(frame)

            # Draw the detected hand landmarks.
            tracker.draw_landmarks(frame)

            if hands:
                hand = hands[0]
                finger_states = tracker.get_finger_states(hand)

                cx, cy = hand["center"]

                cv2.putText(
                    frame,
                    f"Hand: {hand['type']} | Confidence: {hand['score']:.2f}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )

                cv2.putText(
                    frame,
                    f"Center: ({cx}, {cy})",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )

                cv2.putText(
                    frame,
                    f"Finger states: {finger_states}",
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )
            else:
                cv2.putText(
                    frame,
                    "No hand detected",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                )

            cv2.imshow("AirTouch - Hand Tracking", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()
        tracker.hands.close()
        print("AirTouch stopped.")


if __name__ == "__main__":
    main()
