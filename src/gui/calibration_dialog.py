"""Guided calibration window with a live camera preview."""

from datetime import datetime

import cv2
import pyautogui

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from src.calibration import STEPS, Calibrator
from src.gui.camera_worker import open_camera
from src.gui.style import STYLE
from src.vision.hand_tracker import HandTracker


class CalibrationCameraWorker(QThread):
    """Reads the webcam and emits one hand sample per frame (no desktop actions)."""

    frame_ready = Signal(QImage)
    sample_ready = Signal(object)     # dict, or None when no hand is visible
    error_occurred = Signal(str)

    def __init__(self, camera_index=0, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self._running = False
        self._frame_pending = False

    def frame_shown(self):
        self._frame_pending = False

    def stop(self):
        self._running = False
        if self.isRunning() and not self.wait(4000):
            self.requestInterruption()
            self.wait(1500)

    def run(self):
        self._running = True
        tracker = HandTracker(max_num_hands=1)
        camera = open_camera(self.camera_index)

        if not camera.isOpened():
            tracker.hands.close()
            self.error_occurred.emit(
                "Could not open webcam. Check camera connection and permissions."
            )
            return

        try:
            while self._running and not self.isInterruptionRequested():
                success, frame = camera.read()
                if not success:
                    self.error_occurred.emit("Unable to read a webcam frame.")
                    break

                frame = cv2.flip(frame, 1)
                height, width = frame.shape[:2]

                tracker.process_frame(frame)
                hands = tracker.get_hands_info(frame)
                tracker.draw_landmarks(frame)

                if hands:
                    hand = hands[0]
                    self.sample_ready.emit({
                        "lm_list": hand["lm_list"],
                        "finger_states": tracker.get_finger_states(hand),
                        "frame_width": width,
                        "frame_height": height,
                    })
                else:
                    self.sample_ready.emit(None)

                # Skip the preview frame if the window hasn't drawn the last one.
                if not self._frame_pending:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image = QImage(
                        rgb.data, width, height, 3 * width, QImage.Format_RGB888
                    ).copy()
                    self._frame_pending = True
                    self.frame_ready.emit(image)
                self.msleep(1)
        finally:
            camera.release()
            tracker.hands.close()


class CalibrationDialog(QDialog):
    """Walks the user through the calibration steps.

    After exec() returns Accepted, `result_values` holds the new settings and
    `calibrated_at` the timestamp string.
    """

    def __init__(self, start_values, camera_index=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calibrate AirTouch")
        self.setStyleSheet(STYLE)
        self.setMinimumSize(620, 600)

        self.start_values = dict(start_values)
        self.result_values = None
        self.calibrated_at = None

        screen_width, screen_height = pyautogui.size()
        self.calibrator = Calibrator(screen_width, screen_height)
        self.worker = None
        self.camera_index = camera_index
        self._between_steps = False

        self._build_ui()
        self._show_intro()

    # -------------------------------------------------- UI

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        self.step_label = QLabel()
        self.step_label.setObjectName("Section")
        layout.addWidget(self.step_label)

        self.title_label = QLabel()
        self.title_label.setObjectName("Brand")
        self.title_label.setStyleSheet("font-size:21px;")
        layout.addWidget(self.title_label)

        self.instruction_label = QLabel()
        self.instruction_label.setWordWrap(True)
        self.instruction_label.setStyleSheet("color:#C9CAD8; font-size:13px;")
        layout.addWidget(self.instruction_label)

        self.camera_view = QLabel("Camera preview will appear here")
        self.camera_view.setObjectName("Camera")
        self.camera_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_view.setMinimumSize(480, 300)
        self.camera_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.camera_view, 1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        self.feedback_label = QLabel()
        self.feedback_label.setObjectName("Muted")
        self.feedback_label.setWordWrap(True)
        layout.addWidget(self.feedback_label)

        buttons = QHBoxLayout()
        self.skip_btn = QPushButton("Skip this step")
        self.skip_btn.setObjectName("Secondary")
        self.skip_btn.clicked.connect(self._skip_step)
        buttons.addWidget(self.skip_btn)

        buttons.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("Secondary")
        self.cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.cancel_btn)

        self.primary_btn = QPushButton()
        self.primary_btn.clicked.connect(self._primary_clicked)
        buttons.addWidget(self.primary_btn)

        layout.addLayout(buttons)

    def _show_intro(self):
        self.step_label.setText("CALIBRATION")
        self.title_label.setText("Tune AirTouch to your hand")
        self.instruction_label.setText(
            "This takes about 30 seconds. Sit where you normally would, "
            "with your hand clearly visible to the camera. You'll be asked "
            f"to do {len(STEPS)} short steps; each one fills the bar as soon "
            "as AirTouch sees the right pose.\n\n"
            "AirTouch won't move your cursor or click during calibration."
        )
        self.progress.hide()
        self.feedback_label.setText("")
        self.skip_btn.hide()
        self.primary_btn.setText("Start calibration")
        self._mode = "intro"

    def _show_step(self):
        step = self.calibrator.step
        index = self.calibrator.step_index + 1
        self.step_label.setText(f"STEP {index} OF {len(STEPS)}")
        self.title_label.setText(step.title)
        self.instruction_label.setText(step.instruction)
        self.progress.show()
        self.progress.setValue(0)
        self.skip_btn.show()
        self.primary_btn.hide()
        self.feedback_label.setText("Show your hand to the camera.")

    def _show_results(self):
        self._stop_worker()
        values, notes = self.calibrator.results(self.start_values)
        self._pending_values = values

        self.step_label.setText("DONE")
        self.title_label.setText("Calibration complete")
        self.instruction_label.setText(
            "\n".join(f"•  {note}" for note in notes)
            + "\n\nSave to start using these values. You can switch back to "
            "the base settings at any time in Settings."
        )
        self.progress.setValue(100)
        self.skip_btn.hide()
        self.feedback_label.setText("")
        self.camera_view.setPixmap(QPixmap())
        self.camera_view.setText("✓")
        self.camera_view.setStyleSheet("font-size:48px; color:#7DE0AE;")
        self.primary_btn.setText("Save and use")
        self.primary_btn.show()
        self.cancel_btn.setText("Discard")
        self._mode = "results"

    # -------------------------------------------------- actions

    def _primary_clicked(self):
        if self._mode == "intro":
            self._start()
        elif self._mode == "results":
            self.result_values = self._pending_values
            self.calibrated_at = datetime.now().isoformat(timespec="minutes")
            self.accept()

    def _start(self):
        self._mode = "running"
        self.camera_view.setText("Starting camera…")
        self.worker = CalibrationCameraWorker(self.camera_index)
        self.worker.frame_ready.connect(self._update_preview)
        self.worker.sample_ready.connect(self._on_sample)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()
        self._show_step()

    def _skip_step(self):
        if self._mode != "running" or self._between_steps:
            return
        self.calibrator.skip_step()
        self._advance()

    def _advance(self):
        if self.calibrator.done:
            self._show_results()
        else:
            self._show_step()

    def _on_sample(self, sample):
        if self._mode != "running" or self._between_steps:
            return

        if sample is None:
            self.feedback_label.setText("No hand detected — show your hand to the camera.")
            return

        step = self.calibrator.step
        matched = self.calibrator.feed(
            sample["lm_list"],
            sample["finger_states"],
            sample["frame_width"],
            sample["frame_height"],
        )

        self.progress.setValue(int(self.calibrator.progress() * 100))
        count = min(self.calibrator.count(), step.target)

        if matched:
            self.feedback_label.setText(f"Good — {count}/{step.target} {step.unit}")
        else:
            self.feedback_label.setText(
                f"Pose not recognised yet — follow the instruction above. "
                f"({count}/{step.target} {step.unit})"
            )

        if self.calibrator.step_complete():
            self._between_steps = True
            self.feedback_label.setText("✓  Step complete")
            self.calibrator.next_step()
            QTimer.singleShot(900, self._end_pause)

    def _end_pause(self):
        self._between_steps = False
        if self._mode == "running":
            self._advance()

    def _update_preview(self, image):
        if self.worker is not None:
            self.worker.frame_shown()
        if self._mode != "running":
            return
        pixmap = QPixmap.fromImage(image)
        self.camera_view.setPixmap(
            pixmap.scaled(
                self.camera_view.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _on_error(self, message):
        self._stop_worker()
        self._mode = "error"
        self.title_label.setText("Camera problem")
        self.instruction_label.setText(message)
        self.progress.hide()
        self.skip_btn.hide()
        self.primary_btn.hide()
        self.cancel_btn.setText("Close")

    # -------------------------------------------------- cleanup

    def _stop_worker(self):
        if self.worker is not None:
            self.worker.stop()
            self.worker = None

    def done(self, result):
        self._mode = "closed"
        self._stop_worker()
        super().done(result)
