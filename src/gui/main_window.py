"""Modern dark AirTouch desktop interface."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QMessageBox, QSizePolicy
)
from src.gui.camera_worker import CameraWorker


STYLE = """
QMainWindow, QWidget { background: #11121A; color: #F2F2F7; font-family: 'Segoe UI'; }
QFrame#Panel { background: #1B1D29; border: 1px solid #2B2D3D; border-radius: 14px; }
QLabel#Brand { font-size: 25px; font-weight: 700; color: #FFFFFF; }
QLabel#Muted { color: #9294A8; font-size: 12px; }
QLabel#Section { color: #AFA9FF; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
QLabel#Value { color: #F6F5FF; font-size: 16px; font-weight: 600; }
QPushButton { background: #6558D3; color: white; border: 0; border-radius: 9px; padding: 11px 18px; font-weight: 600; }
QPushButton:hover { background: #776BE5; }
QPushButton:disabled { background: #343548; color: #85869A; }
QPushButton#Secondary { background: #292B3A; border: 1px solid #3A3C50; }
QPushButton#Danger { background: #8D3F55; }
QLabel#Camera { background: #090A10; border: 1px solid #303246; border-radius: 12px; color: #85869A; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AirTouch")
        self.setMinimumSize(760, 560)
        self.resize(900, 650)
        self.setStyleSheet(STYLE)
        self.worker = None
        self._build_ui()

    def _panel(self):
        frame = QFrame()
        frame.setObjectName("Panel")
        return frame

    def _build_ui(self):
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(26, 22, 26, 22)
        outer.setSpacing(18)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        brand = QLabel("AirTouch")
        brand.setObjectName("Brand")
        subtitle = QLabel("Gesture control for your desktop")
        subtitle.setObjectName("Muted")
        title_col.addWidget(brand)
        title_col.addWidget(subtitle)
        header.addLayout(title_col)
        header.addStretch()
        self.status_badge = QLabel("●  STOPPED")
        self.status_badge.setStyleSheet("color:#A1A2B3; background:#242634; padding:9px 13px; border-radius:10px; font-weight:700;")
        header.addWidget(self.status_badge)
        outer.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(16)

        camera_panel = self._panel()
        camera_layout = QVBoxLayout(camera_panel)
        camera_layout.setContentsMargins(16, 16, 16, 16)
        camera_label = QLabel("CAMERA PREVIEW")
        camera_label.setObjectName("Section")
        camera_layout.addWidget(camera_label)
        self.camera_view = QLabel("Camera preview will appear here")
        self.camera_view.setObjectName("Camera")
        self.camera_view.setAlignment(Qt.AlignCenter)
        self.camera_view.setMinimumSize(440, 310)
        self.camera_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        camera_layout.addWidget(self.camera_view, 1)
        camera_hint = QLabel("Your video is processed locally on this device.")
        camera_hint.setObjectName("Muted")
        camera_layout.addWidget(camera_hint)
        body.addWidget(camera_panel, 3)

        side = QVBoxLayout()
        side.setSpacing(14)
        gesture_panel = self._panel()
        gl = QVBoxLayout(gesture_panel)
        gl.setContentsMargins(16, 16, 16, 16)
        section = QLabel("GESTURE STATUS")
        section.setObjectName("Section")
        gl.addWidget(section)
        self.current_status = QLabel("Waiting to start")
        self.current_status.setObjectName("Value")
        self.current_status.setWordWrap(True)
        gl.addWidget(self.current_status)
        small = QLabel("Last recognised action")
        small.setObjectName("Muted")
        gl.addWidget(small)
        self.last_action = QLabel("—")
        self.last_action.setStyleSheet("color:#B8B1FF; font-size:14px; font-weight:600;")
        self.last_action.setWordWrap(True)
        gl.addWidget(self.last_action)
        side.addWidget(gesture_panel)

        controls = self._panel()
        cl = QVBoxLayout(controls)
        cl.setContentsMargins(16, 16, 16, 16)
        label = QLabel("CONTROLS")
        label.setObjectName("Section")
        cl.addWidget(label)
        self.start_btn = QPushButton("Start AirTouch")
        self.start_btn.clicked.connect(self.start_camera)
        cl.addWidget(self.start_btn)
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setObjectName("Secondary")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.toggle_pause)
        cl.addWidget(self.pause_btn)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("Danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_camera)
        cl.addWidget(self.stop_btn)
        side.addWidget(controls)
        side.addStretch()
        body.addLayout(side, 2)
        outer.addLayout(body, 1)

        footer = QLabel("AirTouch • Webcam-based hand gesture interaction")
        footer.setObjectName("Muted")
        footer.setAlignment(Qt.AlignCenter)
        outer.addWidget(footer)
        self.setCentralWidget(root)

    def start_camera(self):
        if self.worker and self.worker.isRunning():
            return
        self.worker = CameraWorker()
        self.worker.frame_ready.connect(self.update_preview)
        self.worker.status_changed.connect(self.update_status)
        self.worker.gesture_detected.connect(self.update_gesture)
        self.worker.error_occurred.connect(self.show_error)
        self.worker.start()
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setText("Pause")
        self.current_status.setText("Starting camera…")

    def toggle_pause(self):
        if not self.worker:
            return
        if self.pause_btn.text() == "Pause":
            self.worker.pause()
            self.pause_btn.setText("Resume")
        else:
            self.worker.resume()
            self.pause_btn.setText("Pause")

    def stop_camera(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self.status_badge.setText("●  STOPPED")
        self.status_badge.setStyleSheet("color:#A1A2B3; background:#242634; padding:9px 13px; border-radius:10px; font-weight:700;")
        self.current_status.setText("Stopped")
        self.camera_view.setPixmap(QPixmap())
        self.camera_view.setText("Camera preview will appear here")

    def update_preview(self, image):
        pixmap = QPixmap.fromImage(image)
        self.camera_view.setPixmap(pixmap.scaled(self.camera_view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def update_status(self, state, detail):
        colors = {
            "Active": ("#7DE0AE", "#19382D"),
            "Searching": ("#F0C674", "#3A3020"),
            "Paused": ("#F0C674", "#3A3020"),
            "Stopped": ("#A1A2B3", "#242634"),
        }
        fg, bg = colors.get(state, ("#A1A2B3", "#242634"))
        self.status_badge.setText(f"●  {state.upper()}")
        self.status_badge.setStyleSheet(f"color:{fg}; background:{bg}; padding:9px 13px; border-radius:10px; font-weight:700;")
        self.current_status.setText(detail)

    def update_gesture(self, event):
        self.last_action.setText(event.replace("_", " ").title())

    def show_error(self, message):
        self.current_status.setText("Camera or processing error")
        QMessageBox.warning(self, "AirTouch", message)
        self.stop_camera()

    def closeEvent(self, event):
        self.stop_camera()
        event.accept()