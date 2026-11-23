"""'How to use' window: the gesture guide shown inside the app."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.gui.style import STYLE


# (action, how to do it). Keep in sync with the detectors in src/gestures
# and the mouse / click logic in src/main.py.
GESTURES = [
    (
        "Move the cursor",
        "Point with your index finger, with your thumb and other fingers "
        "tucked in, and move your hand. To reposition without moving the "
        "cursor, relax the pose, move your hand, then point again "
        "(like lifting a mouse).",
    ),
    (
        "Left click",
        "Show an open palm to get ready, then bend your index finger down "
        "while keeping the other fingers open. Open your palm again before "
        "the next click.",
    ),
    (
        "Right click",
        "Lift only your pinky (other fingers closed) and hold it briefly.",
    ),
    (
        "Scroll down",
        "Open palm (all five fingers), then move your hand up. "
        "Scrolls one page.",
    ),
    (
        "Scroll up",
        "Four fingers open with your thumb tucked in, then move your hand "
        "down. Scrolls one page.",
    ),
    (
        "Zoom in",
        "Thumb out to the side (not pointing down) with the other fingers "
        "closed, then slide your hand to the right.",
    ),
    (
        "Zoom out",
        "Index and middle fingers out (ring and pinky closed), then slide "
        "your hand to the left.",
    ),
    (
        "Undo",
        "Thumbs down, and hold it briefly.",
    ),
]

TIPS = [
    "To scroll or zoom again, bring your hand back to where the movement started.",
    "Keep your whole hand in the camera view, in good light.",
    "Emergency stop: push the real mouse into any screen corner.",
    "Gestures feel off? Open Settings and run Calibrate to tune them to your hand.",
]


class HelpDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("How to use AirTouch")
        self.setStyleSheet(STYLE)
        self.setMinimumSize(560, 520)
        self.resize(620, 640)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 18)
        outer.setSpacing(12)

        title = QLabel("How to use AirTouch")
        title.setObjectName("Brand")
        outer.addWidget(title)

        intro = QLabel(
            "Press Start AirTouch, hold your hand up in front of the camera "
            "and use these gestures. Directions are as you see them in the "
            "camera preview."
        )
        intro.setObjectName("Muted")
        intro.setWordWrap(True)
        outer.addWidget(intro)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 6, 0)
        content_layout.setSpacing(12)

        panel = QFrame()
        panel.setObjectName("Panel")
        grid = QGridLayout(panel)
        grid.setContentsMargins(16, 14, 16, 14)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)

        header_action = QLabel("GESTURE")
        header_action.setObjectName("Section")
        header_how = QLabel("HOW")
        header_how.setObjectName("Section")
        grid.addWidget(header_action, 0, 0)
        grid.addWidget(header_how, 0, 1)

        for row, (action, how) in enumerate(GESTURES, start=1):
            action_label = QLabel(action)
            action_label.setStyleSheet("font-weight:600; color:#F6F5FF;")
            action_label.setAlignment(Qt.AlignmentFlag.AlignTop)

            how_label = QLabel(how)
            how_label.setWordWrap(True)
            how_label.setStyleSheet("color:#C9CAD8;")

            grid.addWidget(action_label, row, 0)
            grid.addWidget(how_label, row, 1)

        grid.setColumnStretch(1, 1)
        content_layout.addWidget(panel)

        tips_panel = QFrame()
        tips_panel.setObjectName("Panel")
        tips_layout = QVBoxLayout(tips_panel)
        tips_layout.setContentsMargins(16, 14, 16, 14)

        tips_title = QLabel("TIPS")
        tips_title.setObjectName("Section")
        tips_layout.addWidget(tips_title)

        for tip in TIPS:
            tip_label = QLabel(f"•  {tip}")
            tip_label.setWordWrap(True)
            tip_label.setStyleSheet("color:#C9CAD8;")
            tips_layout.addWidget(tip_label)

        content_layout.addWidget(tips_panel)
        content_layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close_btn = QPushButton("Got it")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        outer.addLayout(buttons)
