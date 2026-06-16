from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)


class PropertiesDialog(QDialog):
    def __init__(
        self, image_width: int, image_height: int, file_path: str | None = None, parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Image Properties")
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint | Qt.WindowType.Dialog
        )
        self._original_width = image_width
        self._original_height = image_height
        self._file_path = file_path
        self._result = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info_group = QGroupBox("Image Information")
        info_layout = QFormLayout(info_group)

        if self._file_path:
            info_layout.addRow("File:", QLabel(self._file_path))

        info_layout.addRow("Width:", QLabel(f"{self._original_width} px"))
        info_layout.addRow("Height:", QLabel(f"{self._original_height} px"))
        total_pixels = self._original_width * self._original_height
        info_layout.addRow("Total Pixels:", QLabel(f"{total_pixels:,}"))

        if total_pixels > 0:
            megapixels = total_pixels / 1_000_000
            info_layout.addRow("Megapixels:", QLabel(f"{megapixels:.2f} MP"))
        info_layout.addRow("DPI:", QLabel("96 (default)"))
        info_layout.addRow("Color Depth:", QLabel("32-bit (ARGB)"))

        layout.addWidget(info_group)

        edit_group = QGroupBox("Edit Properties")
        edit_layout = QFormLayout(edit_group)

        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 10000)
        self._width_spin.setValue(self._original_width)
        edit_layout.addRow("Width (px):", self._width_spin)

        self._height_spin = QSpinBox()
        self._height_spin.setRange(1, 10000)
        self._height_spin.setValue(self._original_height)
        edit_layout.addRow("Height (px):", self._height_spin)

        self._dpi_spin = QSpinBox()
        self._dpi_spin.setRange(1, 1200)
        self._dpi_spin.setValue(96)
        edit_layout.addRow("DPI:", self._dpi_spin)

        self._units_combo = QComboBox()
        self._units_combo.addItems(["Pixels", "Inches", "Centimeters"])
        edit_layout.addRow("Units:", self._units_combo)

        self._color_mode = QComboBox()
        self._color_mode.addItems(["Color (ARGB)", "Black and White"])
        edit_layout.addRow("Color Mode:", self._color_mode)

        layout.addWidget(edit_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        self._result = {
            "width": self._width_spin.value(),
            "height": self._height_spin.value(),
            "dpi": self._dpi_spin.value(),
            "units": self._units_combo.currentText(),
            "color_mode": self._color_mode.currentText(),
        }
        self.accept()

    def result_data(self) -> dict | None:
        return self._result
