"""Settings window: personal/base profile toggle, calibration, sliders."""

import copy
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src.settings import BASE_SETTINGS, SETTING_SPECS, clamp_setting
from src.gui.style import STYLE


class SettingRow:
    """One labelled slider bound to a setting key."""

    def __init__(self, key, grid, row, on_change):
        self.key = key
        self.spec = SETTING_SPECS[key]
        self._on_change = on_change

        self.name = QLabel(self.spec["label"])
        self.name.setStyleSheet("font-weight:600;")

        self.value_label = QLabel()
        self.value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.value_label.setStyleSheet("color:#B8B1FF; font-weight:600;")
        self.value_label.setMinimumWidth(90)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        steps = round((self.spec["maximum"] - self.spec["minimum"]) / self.spec["step"])
        self.slider.setRange(0, steps)
        self.slider.valueChanged.connect(self._slider_moved)

        self.help = QLabel(self.spec["help"])
        self.help.setObjectName("Muted")
        self.help.setWordWrap(True)

        grid.addWidget(self.name, row, 0)
        grid.addWidget(self.value_label, row, 1)
        grid.addWidget(self.slider, row + 1, 0, 1, 2)
        grid.addWidget(self.help, row + 2, 0, 1, 2)

    def _to_value(self, position):
        return clamp_setting(
            self.key, self.spec["minimum"] + position * self.spec["step"]
        )

    def set_value(self, value):
        position = round((value - self.spec["minimum"]) / self.spec["step"])
        self.slider.blockSignals(True)
        self.slider.setValue(position)
        self.slider.blockSignals(False)
        self._show(value)

    def _show(self, value):
        text = self.spec["fmt"].format(value)
        if value == BASE_SETTINGS[self.key]:
            text += "  (base)"
        self.value_label.setText(text)

    def _slider_moved(self, position):
        value = self._to_value(position)
        self._show(value)
        self._on_change(self.key, value)

    def set_enabled(self, enabled):
        for widget in (self.slider, self.name, self.value_label):
            widget.setEnabled(enabled)


class SettingsDialog(QDialog):
    """Edits a copy of UserSettings; read `result_settings` after Accepted.

    prepare_calibration: callable returning True if calibration may start
    (the main window uses it to stop the camera first).
    """

    def __init__(self, user_settings, prepare_calibration=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AirTouch settings")
        self.setStyleSheet(STYLE)
        self.setMinimumSize(560, 600)
        self.resize(600, 720)

        self.working = copy.deepcopy(user_settings)
        self.result_settings = None
        self._prepare_calibration = prepare_calibration

        self._build_ui()
        self._refresh()

    # -------------------------------------------------- UI

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 18)
        outer.setSpacing(12)

        title = QLabel("Settings")
        title.setObjectName("Brand")
        outer.addWidget(title)

        # Profile panel
        profile = QFrame()
        profile.setObjectName("Panel")
        pl = QVBoxLayout(profile)
        pl.setContentsMargins(16, 14, 16, 14)
        pl.setSpacing(8)

        section = QLabel("PROFILE")
        section.setObjectName("Section")
        pl.addWidget(section)

        self.personal_toggle = QCheckBox(
            "Use my personal settings (calibration and adjustments)"
        )
        self.personal_toggle.toggled.connect(self._toggle_personal)
        pl.addWidget(self.personal_toggle)

        self.profile_hint = QLabel()
        self.profile_hint.setObjectName("Muted")
        self.profile_hint.setWordWrap(True)
        pl.addWidget(self.profile_hint)

        row = QHBoxLayout()
        self.calibrate_btn = QPushButton("Calibrate…")
        self.calibrate_btn.clicked.connect(self._calibrate)
        row.addWidget(self.calibrate_btn)

        self.reset_btn = QPushButton("Reset to base settings")
        self.reset_btn.setObjectName("Secondary")
        self.reset_btn.clicked.connect(self._reset)
        row.addWidget(self.reset_btn)
        row.addStretch()
        pl.addLayout(row)

        outer.addWidget(profile)

        # Sliders
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 6, 0)

        adjust = QFrame()
        adjust.setObjectName("Panel")
        grid = QGridLayout(adjust)
        grid.setContentsMargins(16, 14, 16, 14)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)

        adjust_title = QLabel("ADJUSTMENTS")
        adjust_title.setObjectName("Section")
        grid.addWidget(adjust_title, 0, 0, 1, 2)

        self.adjust_hint = QLabel()
        self.adjust_hint.setObjectName("Muted")
        self.adjust_hint.setWordWrap(True)
        grid.addWidget(self.adjust_hint, 1, 0, 1, 2)

        self.rows = {}
        grid_row = 2
        for key in SETTING_SPECS:
            spacer = QLabel("")
            spacer.setFixedHeight(6)
            grid.addWidget(spacer, grid_row, 0)
            self.rows[key] = SettingRow(key, grid, grid_row + 1, self._value_changed)
            grid_row += 4

        cl.addWidget(adjust)
        cl.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        # Bottom buttons
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("Secondary")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)

        save = QPushButton("Save")
        save.clicked.connect(self._save)
        buttons.addWidget(save)
        outer.addLayout(buttons)

    def _refresh(self):
        personal = self.working.use_personal

        self.personal_toggle.blockSignals(True)
        self.personal_toggle.setChecked(personal)
        self.personal_toggle.blockSignals(False)

        if self.working.calibrated_at:
            try:
                when = datetime.fromisoformat(self.working.calibrated_at)
                when_text = when.strftime("%d %b %Y at %H:%M")
            except ValueError:
                when_text = self.working.calibrated_at
            calibration_text = f"Calibrated on {when_text}."
        else:
            calibration_text = "Not calibrated yet."

        if personal:
            self.profile_hint.setText(
                f"{calibration_text} AirTouch is using your personal values "
                "below. Untick to go back to the base settings (your values "
                "are kept for later)."
            )
            self.adjust_hint.setText("Drag a slider to fine-tune a value.")
        else:
            self.profile_hint.setText(
                f"{calibration_text} AirTouch is using the base settings. "
                "Tick the box or run Calibrate to use values tuned to you."
            )
            self.adjust_hint.setText(
                "Showing the base settings. Tick “Use my personal settings” "
                "to adjust them."
            )

        values = self.working.effective()
        for key, row in self.rows.items():
            row.set_value(values[key])
            row.set_enabled(personal)

    # -------------------------------------------------- actions

    def _toggle_personal(self, checked):
        self.working.use_personal = checked
        self._refresh()

    def _value_changed(self, key, value):
        if self.working.use_personal:
            self.working.personal[key] = value

    def _reset(self):
        answer = QMessageBox.question(
            self,
            "Reset to base settings",
            "This removes your calibration and adjustments and goes back to "
            "the base settings. Continue?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.working.reset_to_base()
            self._refresh()

    def _calibrate(self):
        if self._prepare_calibration and not self._prepare_calibration():
            return

        # Imported here so the Settings window opens instantly.
        from src.gui.calibration_dialog import CalibrationDialog

        start = (
            self.working.personal if self.working.use_personal else BASE_SETTINGS
        )
        dialog = CalibrationDialog(start, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_values:
            self.working.personal = dict(dialog.result_values)
            self.working.use_personal = True
            self.working.calibrated_at = dialog.calibrated_at
            # "Save and use" in the calibration window saves immediately.
            self._save()

    def _save(self):
        self.result_settings = self.working
        self.accept()
