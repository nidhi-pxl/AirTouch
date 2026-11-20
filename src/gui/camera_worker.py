"""Background camera and gesture-processing worker for the AirTouch GUI.

The existing gesture detector implementations are imported unchanged.
"""
import math
import time
from collections import deque
from statistics import median

import cv2
import pyautogui
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from src.vision.hand_tracker import HandTracker
from src.gestures.swipe_detector import SwipeDetector
from src.gestures.zoom_detector import ZoomDetector
from src.gestures.pinky_detector import PinkyDetector
from src.gestures.thumbs_down_detector import ThumbsDownDetector
from src.interaction.action_mapper import ActionMapper


ACTIVATION_FRAMES = 3
DEACTIVATION_FRAMES = 4
FILTER_FRAMES = 5
DEAD_ZONE = 5
CURSOR_SENSITIVITY = 0.75
LEFT_CLICK_BENT_ANGLE = 145
LEFT_CLICK_CONFIRM_FRAMES = 3
LEFT_CLICK_COOLDOWN = 0.6

pyautogui.FAILSAFE = True


def calculate_angle(a, b, c):
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    ma, mb = math.hypot(*ba), math.hypot(*bc)
    if ma == 0 or mb == 0:
        return None
    cosine = (ba[0] * bc[0] + ba[1] * bc[1]) / (ma * mb)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


class CameraWorker(QThread):
    frame_ready = Signal(QImage)
    status_changed = Signal(str, str)
    gesture_detected = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, camera_index=0, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self._running = False
        self._paused = False

    def pause(self):
        self._paused = True
        self.status_changed.emit("Paused", "Camera processing is paused")

    def resume(self):
        self._paused = False
        self.status_changed.emit("Active", "Waiting for gesture")

    def stop(self):
        self._running = False
        self.wait(3000)

    def _emit_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
        self.frame_ready.emit(image)

    def run(self):
        self._running = True
        tracker = HandTracker(max_num_hands=1)
        camera = cv2.VideoCapture(self.camera_index)
        if not camera.isOpened():
            tracker.hands.close()
            self.error_occurred.emit("Could not open webcam. Check that it is connected and not being used by another app.")
            self._running = False
            return

        scroll_detector = SwipeDetector(movement_threshold=50)
        zoom_detector = ZoomDetector()
        pinky_detector = PinkyDetector()
        thumbs_down_detector = ThumbsDownDetector()
        mapper = ActionMapper(dry_run=False)

        screen_w, screen_h = pyautogui.size()
        mouse_active = False
        positive_frames = negative_frames = 0
        left_click_frames = 0
        left_click_armed = False
        last_left_click_time = 0.0
        x_history, y_history = deque(maxlen=FILTER_FRAMES), deque(maxlen=FILTER_FRAMES)
        hand_anchor_x = hand_anchor_y = None
        screen_anchor_x = screen_anchor_y = None
        last_cursor_x = last_cursor_y = None
        last_event = "Waiting for gesture"

        self.status_changed.emit("Active", "Camera connected")

        try:
            while self._running and not self.isInterruptionRequested():
                if self._paused:
                    self.msleep(80)
                    continue

                ok, frame = camera.read()
                if not ok:
                    self.error_occurred.emit("Unable to read a webcam frame.")
                    break

                frame = cv2.flip(frame, 1)
                fh, fw = frame.shape[:2]
                tracker.process_frame(frame)
                hands = tracker.get_hands_info(frame)
                tracker.draw_landmarks(frame)

                if hands:
                    hand = hands[0]
                    fingers = tracker.get_finger_states(hand)

                    # Existing team gesture detectors are used without changing their logic.
                    events = (
                        scroll_detector.update(hand, fingers),
                        zoom_detector.update(hand, fingers),
                        pinky_detector.update(hand, fingers),
                        thumbs_down_detector.update(hand, fingers),
                    )
                    for event in events:
                        if event:
                            mapper.handle_event(event)
                            last_event = event
                            self.gesture_detected.emit(event)

                    # Existing mouse activation pose.
                    mouse_pose = fingers == [0, 1, 0, 0, 0]
                    lm = hand["lm_list"]
                    angle = calculate_angle(lm[5], lm[6], lm[8]) if len(lm) > 8 else None
                    click_pose = (
                        fingers[0] == 1 and fingers[1] == 0
                        and fingers[2] == 1 and fingers[3] == 1 and fingers[4] == 1
                        and angle is not None and angle < LEFT_CLICK_BENT_ANGLE
                    )
                    open_palm = fingers == [1, 1, 1, 1, 1]

                    if open_palm:
                        left_click_armed = True
                        left_click_frames = 0
                    if left_click_armed and click_pose:
                        left_click_frames += 1
                    else:
                        left_click_frames = 0

                    now = time.monotonic()
                    if left_click_armed and left_click_frames >= LEFT_CLICK_CONFIRM_FRAMES and now - last_left_click_time >= LEFT_CLICK_COOLDOWN:
                        pyautogui.click(button="left")
                        last_left_click_time = now
                        left_click_armed = False
                        left_click_frames = 0
                        last_event = "LEFT_CLICK"
                        self.gesture_detected.emit(last_event)

                    if click_pose:
                        mouse_active = False
                        positive_frames = negative_frames = 0
                        hand_anchor_x = hand_anchor_y = screen_anchor_x = screen_anchor_y = None
                        last_cursor_x = last_cursor_y = None
                        x_history.clear()
                        y_history.clear()
                    else:
                        if mouse_pose:
                            positive_frames += 1
                            negative_frames = 0
                        else:
                            negative_frames += 1
                            positive_frames = 0

                        if positive_frames >= ACTIVATION_FRAMES and not mouse_active:
                            hand_anchor_x, hand_anchor_y = lm[8][0], lm[8][1]
                            screen_anchor_x, screen_anchor_y = pyautogui.position()
                            last_cursor_x, last_cursor_y = screen_anchor_x, screen_anchor_y
                            x_history.clear()
                            y_history.clear()
                            mouse_active = True

                        if negative_frames >= DEACTIVATION_FRAMES and mouse_active:
                            mouse_active = False
                            hand_anchor_x = hand_anchor_y = screen_anchor_x = screen_anchor_y = None
                            last_cursor_x = last_cursor_y = None
                            x_history.clear()
                            y_history.clear()

                        if mouse_active:
                            x_history.append(lm[8][0])
                            y_history.append(lm[8][1])
                            if len(x_history) == FILTER_FRAMES:
                                fx, fy = median(x_history), median(y_history)
                                tx = int(screen_anchor_x + (fx - hand_anchor_x) * screen_w / fw * CURSOR_SENSITIVITY)
                                ty = int(screen_anchor_y + (fy - hand_anchor_y) * screen_h / fh * CURSOR_SENSITIVITY)
                                tx = max(0, min(screen_w - 1, tx))
                                ty = max(0, min(screen_h - 1, ty))
                                if abs(tx - last_cursor_x) > DEAD_ZONE or abs(ty - last_cursor_y) > DEAD_ZONE:
                                    pyautogui.moveTo(tx, ty, duration=0)
                                    last_cursor_x, last_cursor_y = tx, ty

                    mode = "CURSOR CONTROL ACTIVE" if mouse_active else "CURSOR CONTROL INACTIVE"
                    cv2.putText(frame, mode, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, .55, (100, 230, 160) if mouse_active else (170, 170, 170), 2)
                    cv2.putText(frame, f"Last action: {last_event}", (12, 55), cv2.FONT_HERSHEY_SIMPLEX, .48, (240, 240, 240), 1)
                    self.status_changed.emit("Active", last_event)
                else:
                    positive_frames = 0
                    negative_frames += 1
                    scroll_detector.reset()
                    zoom_detector.reset()
                    pinky_detector.reset()
                    thumbs_down_detector.reset()
                    left_click_frames = 0
                    left_click_armed = False
                    if negative_frames >= DEACTIVATION_FRAMES:
                        mouse_active = False
                        hand_anchor_x = hand_anchor_y = screen_anchor_x = screen_anchor_y = None
                        last_cursor_x = last_cursor_y = None
                        x_history.clear()
                        y_history.clear()
                    cv2.putText(frame, "No hand detected", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, .6, (80, 100, 240), 2)
                    cv2.putText(frame, "Show your hand to begin", (12, 55), cv2.FONT_HERSHEY_SIMPLEX, .48, (230, 230, 230), 1)
                    self.status_changed.emit("Searching", "No hand detected")

                self._emit_frame(frame)
                self.msleep(1)

        except pyautogui.FailSafeException:
            self.error_occurred.emit("PyAutoGUI safety stop activated (mouse moved to a screen corner).")
        except Exception as exc:
            self.error_occurred.emit(f"AirTouch stopped because of an error: {exc}")
        finally:
            camera.release()
            tracker.hands.close()
            self._running = False
            self.status_changed.emit("Stopped", "Camera released")