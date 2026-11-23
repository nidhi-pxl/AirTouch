"""Shared Qt stylesheet for the AirTouch windows."""

STYLE = """
QMainWindow, QWidget {
    background: #11121A;
    color: #F2F2F7;
    font-family: 'Segoe UI';
}

QLabel {
    background: transparent;
    border: none;
}

QFrame#Panel {
    background: #1B1D29;
    border: 1px solid #2B2D3D;
    border-radius: 14px;
}

QLabel#Brand {
    font-size: 25px;
    font-weight: 700;
    color: #FFFFFF;
}

QLabel#Muted {
    color: #9294A8;
    font-size: 12px;
}

QLabel#Section {
    color: #AFA9FF;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}

QLabel#Value {
    color: #F6F5FF;
    font-size: 16px;
    font-weight: 600;
}

QPushButton {
    background: #6558D3;
    color: white;
    border: 0;
    border-radius: 9px;
    padding: 11px 18px;
    font-weight: 600;
}

QPushButton:hover {
    background: #776BE5;
}

QPushButton:disabled {
    background: #343548;
    color: #85869A;
}

QPushButton#Secondary {
    background: #292B3A;
    border: 1px solid #3A3C50;
}

QPushButton#Danger {
    background: #8D3F55;
}

QLabel#Camera {
    background: #090A10;
    border: 1px solid #303246;
    border-radius: 12px;
    color: #85869A;
}

QDialog {
    background: #11121A;
    color: #F2F2F7;
}

QPushButton#Small {
    background: #292B3A;
    border: 1px solid #3A3C50;
    padding: 8px 12px;
}

QPushButton#Small:hover, QPushButton#Secondary:hover {
    background: #343648;
}

QCheckBox {
    background: transparent;
    spacing: 9px;
    font-weight: 600;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #4A4C63;
    background: #242634;
}

QCheckBox::indicator:checked {
    background: #6558D3;
    border: 1px solid #776BE5;
}

QSlider {
    background: transparent;
}

QSlider::groove:horizontal {
    height: 6px;
    border-radius: 3px;
    background: #2B2D3D;
}

QSlider::sub-page:horizontal {
    border-radius: 3px;
    background: #6558D3;
}

QSlider::sub-page:horizontal:disabled {
    background: #3A3C50;
}

QSlider::handle:horizontal {
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: #F2F2F7;
}

QSlider::handle:horizontal:disabled {
    background: #6E7085;
}

QProgressBar {
    height: 10px;
    border: none;
    border-radius: 5px;
    background: #2B2D3D;
    color: transparent;
}

QProgressBar::chunk {
    border-radius: 5px;
    background: #7DE0AE;
}

QScrollArea {
    background: transparent;
    border: none;
}
"""
