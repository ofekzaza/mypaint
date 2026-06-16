from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ResizeDialog(QDialog):
    def __init__(self, image_width: int, image_height: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resize and Skew")
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint | Qt.WindowType.Dialog
        )
        self._original_width = image_width
        self._original_height = image_height
        self._result = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        resize_group = QGroupBox("Resize")
        resize_layout = QVBoxLayout(resize_group)

        method_layout = QHBoxLayout()
        self._percentage_radio = QRadioButton("Percentage")
        self._pixels_radio = QRadioButton("Pixels")
        self._pixels_radio.setChecked(True)
        method_group = QButtonGroup(self)
        method_group.addButton(self._percentage_radio)
        method_group.addButton(self._pixels_radio)
        method_layout.addWidget(self._percentage_radio)
        method_layout.addWidget(self._pixels_radio)
        method_layout.addStretch()
        resize_layout.addLayout(method_layout)

        dims_layout = QHBoxLayout()
        dims_layout.addWidget(QLabel("Horizontal:"))
        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 10000)
        self._width_spin.setValue(self._original_width)
        dims_layout.addWidget(self._width_spin)

        dims_layout.addWidget(QLabel("Vertical:"))
        self._height_spin = QSpinBox()
        self._height_spin.setRange(1, 10000)
        self._height_spin.setValue(self._original_height)
        dims_layout.addWidget(self._height_spin)
        resize_layout.addLayout(dims_layout)

        self._aspect_ratio = QCheckBox("Maintain aspect ratio")
        self._aspect_ratio.setChecked(True)
        resize_layout.addWidget(self._aspect_ratio)

        self._percentage_width = QSpinBox()
        self._percentage_width.setRange(1, 500)
        self._percentage_width.setValue(100)
        self._percentage_width.setSuffix("%")
        self._percentage_height = QSpinBox()
        self._percentage_height.setRange(1, 500)
        self._percentage_height.setValue(100)
        self._percentage_height.setSuffix("%")

        pct_layout = QHBoxLayout()
        pct_layout.addWidget(QLabel("Horizontal:"))
        pct_layout.addWidget(self._percentage_width)
        pct_layout.addWidget(QLabel("Vertical:"))
        pct_layout.addWidget(self._percentage_height)
        pct_layout.addStretch()

        self._percentage_widget = QWidget()
        self._percentage_widget.setLayout(pct_layout)
        self._percentage_widget.setVisible(False)
        resize_layout.addWidget(self._percentage_widget)

        layout.addWidget(resize_group)

        skew_group = QGroupBox("Skew (Degrees)")
        skew_layout = QHBoxLayout(skew_group)

        skew_layout.addWidget(QLabel("Horizontal:"))
        self._skew_horizontal = QSlider(Qt.Orientation.Horizontal)
        self._skew_horizontal.setRange(-89, 89)
        self._skew_horizontal.setValue(0)
        self._skew_horizontal.setTickPosition(QSlider.TickPosition.TicksBelow)
        skew_layout.addWidget(self._skew_horizontal)
        self._skew_h_label = QLabel("0°")
        skew_layout.addWidget(self._skew_h_label)

        skew_layout.addWidget(QLabel("Vertical:"))
        self._skew_vertical = QSlider(Qt.Orientation.Horizontal)
        self._skew_vertical.setRange(-89, 89)
        self._skew_vertical.setValue(0)
        self._skew_vertical.setTickPosition(QSlider.TickPosition.TicksBelow)
        skew_layout.addWidget(self._skew_vertical)
        self._skew_v_label = QLabel("0°")
        skew_layout.addWidget(self._skew_v_label)

        layout.addWidget(skew_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._percentage_radio.toggled.connect(
            lambda checked: self._percentage_widget.setVisible(checked)
        )
        self._aspect_ratio.toggled.connect(self._on_aspect_toggled)
        self._width_spin.valueChanged.connect(self._on_width_changed)
        self._height_spin.valueChanged.connect(self._on_height_changed)
        self._skew_horizontal.valueChanged.connect(lambda v: self._skew_h_label.setText(f"{v}°"))
        self._skew_vertical.valueChanged.connect(lambda v: self._skew_v_label.setText(f"{v}°"))

        self._percentage_width.valueChanged.connect(self._on_pct_width_changed)
        self._percentage_height.valueChanged.connect(self._on_pct_height_changed)

    def _on_aspect_toggled(self, checked: bool) -> None:
        if checked:
            self._on_width_changed(self._width_spin.value())

    def _on_width_changed(self, value: int) -> None:
        if self._aspect_ratio.isChecked():
            ratio = self._original_height / self._original_width
            self._height_spin.blockSignals(True)
            self._height_spin.setValue(max(1, int(value * ratio)))
            self._height_spin.blockSignals(False)

    def _on_height_changed(self, value: int) -> None:
        if self._aspect_ratio.isChecked():
            ratio = self._original_width / self._original_height
            self._width_spin.blockSignals(True)
            self._width_spin.setValue(max(1, int(value * ratio)))
            self._width_spin.blockSignals(False)

    def _on_pct_width_changed(self, value: int) -> None:
        if self._aspect_ratio.isChecked():
            self._percentage_height.blockSignals(True)
            self._percentage_height.setValue(value)
            self._percentage_height.blockSignals(False)
            w = int(self._original_width * value / 100)
            self._width_spin.blockSignals(True)
            self._width_spin.setValue(max(1, w))
            self._width_spin.blockSignals(False)
            h = int(self._original_height * value / 100)
            self._height_spin.blockSignals(True)
            self._height_spin.setValue(max(1, h))
            self._height_spin.blockSignals(False)

    def _on_pct_height_changed(self, value: int) -> None:
        if self._aspect_ratio.isChecked():
            self._percentage_width.blockSignals(True)
            self._percentage_width.setValue(value)
            self._percentage_width.blockSignals(False)
            w = int(self._original_width * value / 100)
            self._width_spin.blockSignals(True)
            self._width_spin.setValue(max(1, w))
            self._width_spin.blockSignals(False)
            h = int(self._original_height * value / 100)
            self._height_spin.blockSignals(True)
            self._height_spin.setValue(max(1, h))
            self._height_spin.blockSignals(False)

    def _accept(self) -> None:
        use_pixels = self._pixels_radio.isChecked()
        if use_pixels:
            w = self._width_spin.value()
            h = self._height_spin.value()
        else:
            w = int(self._original_width * self._percentage_width.value() / 100)
            h = int(self._original_height * self._percentage_height.value() / 100)
        skew_h = self._skew_horizontal.value()
        skew_v = self._skew_vertical.value()
        self._result = {
            "width": max(1, w),
            "height": max(1, h),
            "skew_h": skew_h,
            "skew_v": skew_v,
        }
        self.accept()

    def result_data(self) -> dict | None:
        return self._result
