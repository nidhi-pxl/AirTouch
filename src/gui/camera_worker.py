"""Background camera worker containing AirTouch's original processing loop.

The gesture detector implementations and their update/reset calls are kept
unchanged. OpenCV's standalone window is replaced by a Qt image signal so the
existing camera preview can be displayed inside the desktop GUI.
"""

import sys
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

from src.main import (
    ACTIVATION_FRAMES,
    DEACTIVATION_FRAMES,
    LEFT_CLICK_COOLDOWN,
    detect_mouse_gesture,
    get_index_tip,
    detect_left_click_gesture,
    is_open_palm,
    reset_cursor_anchors,
)
from src.settings import BASE_SETTINGS


pyautogui.FAILSAFE = True

# PyAutoGUI sleeps for PAUSE seconds (default 0.1) after *every* call.
# The cursor is moved once per camera frame, so the default capped the
# processing loop at under 10 FPS whenever the cursor moved.
pyautogui.PAUSE = 0


def open_camera(camera_index=0):
    """Open the webcam at 640x480.

    On Windows, OpenCV's default backend (Media Foundation) can take many
    seconds to open some webcams; DirectShow usually opens almost instantly.
    Falls back to the default backend if DirectShow can't open the camera.
    """
    camera = None
    if sys.platform == "win32":
        camera = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not camera.isOpened():
            camera.release()
            camera = None

    if camera is None:
        camera = cv2.VideoCapture(camera_index)

    if camera.isOpened():
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        # Keep only the newest frame so the preview never lags behind.
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    return camera


class CameraWorker(QThread):
    """Run webcam tracking and desktop actions without freezing the GUI."""

    frame_ready = Signal(QImage)
    status_changed = Signal(str, str)
    gesture_detected = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, camera_index=0, settings=None, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self._running = False
        self._paused = False
        self._settings = dict(BASE_SETTINGS)
        if settings:
            self._settings.update(settings)
        self._pending_settings = None

        # Only one preview frame may be waiting for the window at a time;
        # newer frames are skipped until the window has drawn it.
        self._frame_pending = False
        self._last_status = None

    def frame_shown(self):
        """Called by the window after it has drawn a preview frame."""
        self._frame_pending = False

    def _emit_status(self, state, detail):
        """Send a status update only when it actually changes."""
        status = (state, detail)
        if status != self._last_status:
            self._last_status = status
            self.status_changed.emit(state, detail)

    def apply_settings(self, settings):
        """Queue new tuning values; the camera loop picks them up next frame."""
        self._pending_settings = dict(settings)

    def pause(self):
        self._paused = True
        self._emit_status("Paused", "Gesture processing paused")

    def resume(self):
        self._paused = False
        self._emit_status("Active", "Resumed — waiting for gesture")

    def request_stop(self):
        """Ask the camera loop to finish, without waiting for it."""
        self._running = False

    def stop(self):
        """Request shutdown and wait briefly for the camera loop to finish."""
        self._running = False
        if self.isRunning() and not self.wait(4000):
            self.requestInterruption()
            self.wait(1500)

    def _publish_frame(self, frame):
        """Convert an OpenCV BGR frame to a detached Qt image.

        Skipped while the window is still drawing the previous frame, so
        frames can never pile up and freeze the window.
        """
        if self._frame_pending:
            return

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb_frame.shape
        bytes_per_line = channels * width

        image = QImage(
            rgb_frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888,
        ).copy()

        self._frame_pending = True
        self.frame_ready.emit(image)

    def run(self):
        self._running = True

        tracker = HandTracker(max_num_hands=1)
        camera = open_camera(self.camera_index)

        # Tuning values: base settings, or the user's calibrated profile.
        cfg = dict(self._settings)

        # Gesture detectors. Scroll and zoom distances are fractions of
        # hand size, so they work at any distance from the camera.
        scroll_detector = SwipeDetector(
            movement_threshold=cfg["scroll_threshold"],
        )
        zoom_detector = ZoomDetector(
            movement_threshold=cfg["zoom_threshold"],
        )
        pinky_detector = PinkyDetector(hold_frames=cfg["pose_hold_frames"])
        thumbs_down_detector = ThumbsDownDetector(
            hold_frames=cfg["pose_hold_frames"],
        )

        action_mapper = ActionMapper(dry_run=False)

        screen_width, screen_height = pyautogui.size()

        # Existing mouse state.
        mouse_active = False
        positive_frames = 0
        negative_frames = 0

        # Existing left-click state.
        left_click_frames = 0
        left_click_armed = False
        left_click_detected = False
        last_left_click_time = 0.0

        # Existing cursor smoothing.
        x_history = deque(maxlen=cfg["filter_frames"])
        y_history = deque(maxlen=cfg["filter_frames"])

        # Existing relative cursor anchors.
        (
            hand_anchor_x,
            hand_anchor_y,
            screen_anchor_x,
            screen_anchor_y,
            last_cursor_x,
            last_cursor_y,
        ) = reset_cursor_anchors()

        last_action = "Waiting for gesture"

        if not camera.isOpened():
            tracker.hands.close()
            self._running = False
            self.error_occurred.emit("Could not open webcam. Check camera connection and permissions.")
            self._emit_status("Stopped", "Camera unavailable")
            return

        print("-----------------------------------")
        print("AirTouch GUI started.")
        print("-----------------------------------")
        print("Mouse: Thumb closed, index open, other fingers closed.")
        print("Left-click: Open palm, then bend index finger.")
        print("Right-click: Pinky detector.")
        print("Zoom in: thumb out, slide thumb right.")
        print("Zoom out: index + middle out, slide left.")
        print("Undo: Thumbs-down detector.")
        print("Scroll: Swipe detector.")
        print("-----------------------------------")

        self._emit_status("Active", "Camera connected — show your hand")

        try:
            while self._running and not self.isInterruptionRequested():

                # Pause processing while keeping the worker and GUI responsive.
                if self._paused:
                    self.msleep(40)
                    continue

                # Apply settings changed in the Settings window while running.
                if self._pending_settings is not None:
                    cfg.update(self._pending_settings)
                    self._settings = dict(cfg)
                    self._pending_settings = None

                    scroll_detector.movement_threshold = cfg["scroll_threshold"]
                    zoom_detector.movement_threshold = cfg["zoom_threshold"]
                    pinky_detector.hold_frames = cfg["pose_hold_frames"]
                    thumbs_down_detector.hold_frames = cfg["pose_hold_frames"]

                    if x_history.maxlen != cfg["filter_frames"]:
                        x_history = deque(maxlen=cfg["filter_frames"])
                        y_history = deque(maxlen=cfg["filter_frames"])

                success, frame = camera.read()

                if not success:
                    self.error_occurred.emit("Unable to read a webcam frame.")
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
                    # EXISTING GESTURE DETECTORS
                    # Detector implementations unchanged.
                    # ----------------------------------

                    scroll_event = scroll_detector.update(
                        hand,
                        finger_states,
                    )
                    action_mapper.handle_event(scroll_event)

                    zoom_event = zoom_detector.update(hand, finger_states)
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

                    # Send recognised detector events to the GUI.
                    for event in (
                        scroll_event,
                        zoom_event,
                        right_click_event,
                        undo_event,
                    ):
                        if event:
                            last_action = event
                            self.gesture_detected.emit(event)

                    # ----------------------------------
                    # EXISTING MOUSE AND LEFT-CLICK LOGIC
                    # ----------------------------------

                    mouse_gesture = detect_mouse_gesture(
                        hand,
                        finger_states,
                    )

                    left_click_pose, index_angle = detect_left_click_gesture(
                        hand,
                        finger_states,
                        bent_angle=cfg["click_bend_angle"],
                    )

                    open_palm = is_open_palm(finger_states)

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
                        and left_click_frames >= cfg["click_confirm_frames"]
                    )

                    # Execute exactly one click, respecting cooldown.
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

                        last_action = "LEFT_CLICK"
                        self.gesture_detected.emit(last_action)
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

                                if len(x_history) == x_history.maxlen:
                                    filtered_x = median(x_history)
                                    filtered_y = median(y_history)

                                    delta_x = filtered_x - hand_anchor_x
                                    delta_y = filtered_y - hand_anchor_y

                                    target_x = int(
                                        screen_anchor_x
                                        + delta_x
                                        * screen_width
                                        / frame_width
                                        * cfg["cursor_sensitivity"]
                                    )

                                    target_y = int(
                                        screen_anchor_y
                                        + delta_y
                                        * screen_height
                                        / frame_height
                                        * cfg["cursor_sensitivity"]
                                    )

                                    # Keep 1 px away from the screen edges:
                                    # PyAutoGUI's fail-safe fires when the
                                    # cursor sits exactly in a corner, which
                                    # used to stop AirTouch whenever the hand
                                    # pushed the cursor into one.
                                    target_x = max(
                                        1,
                                        min(screen_width - 2, target_x),
                                    )
                                    target_y = max(
                                        1,
                                        min(screen_height - 2, target_y),
                                    )

                                    dx = target_x - last_cursor_x
                                    dy = target_y - last_cursor_y

                                    if (
                                        abs(dx) > cfg["dead_zone"]
                                        or abs(dy) > cfg["dead_zone"]
                                    ):
                                        pyautogui.moveTo(
                                            target_x,
                                            target_y,
                                            duration=0,
                                        )

                                        last_cursor_x = target_x
                                        last_cursor_y = target_y

                    # ----------------------------------
                    # CAMERA PREVIEW OVERLAYS
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

                    # Show when a zoom pose is recognised and how far the
                    # slide has got, so users can see what the detector sees.
                    if zoom_detector.feedback:
                        cv2.putText(
                            frame,
                            zoom_detector.feedback,
                            (10, 205),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (255, 200, 0),
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
                        angle_text = f"Index bend angle: {index_angle:.1f}"
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
                            f"{cfg['click_confirm_frames']}"
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
                        f"Hand: {hand['type']} | Confidence: {hand['score']:.2f}",
                        (10, 170),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        1,
                    )

                    current_status = (
                        "Cursor control active"
                        if mouse_active
                        else "Hand detected"
                    )
                    self._emit_status("Active", current_status)

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

                    # Reset existing gesture detectors.
                    zoom_detector.reset()
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

                    self._emit_status("Searching", "No hand detected")

                # Publish the frame to the GUI instead of opening cv2.imshow().
                self._publish_frame(frame)
                self.msleep(1)

        except pyautogui.FailSafeException:
            self.error_occurred.emit(
                "Mouse control stopped by the PyAutoGUI fail-safe."
            )
        except Exception as exc:
            self.error_occurred.emit(
                f"AirTouch encountered an error: {type(exc).__name__}: {exc}"
            )
        finally:
            self._running = False
            camera.release()
            tracker.hands.close()
            self._emit_status("Stopped", "Camera released")
            print("AirTouch stopped.")
