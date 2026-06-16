from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QHBoxLayout,
    QSpinBox,
    QToolButton,
    QWidget,
)


class TextToolbar(QWidget):
    font_changed = Signal(QFont)
    bold_changed = Signal(bool)
    italic_changed = Signal(bool)
    underline_changed = Signal(bool)
    strikeout_changed = Signal(bool)
    color_changed = Signal(QColor)
    background_mode_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Text")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        if parent:
            self.setParent(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._font_combo = QComboBox()
        self._font_combo.addItems(QFontDatabase().families())
        self._font_combo.setCurrentText("Sans")
        self._font_combo.setMinimumWidth(140)
        self._font_combo.currentTextChanged.connect(self._on_font_changed)
        layout.addWidget(self._font_combo)

        self._size_spin = QSpinBox()
        self._size_spin.setRange(1, 200)
        self._size_spin.setValue(12)
        self._size_spin.valueChanged.connect(self._on_font_changed)
        layout.addWidget(self._size_spin)

        self._bold_btn = QToolButton()
        self._bold_btn.setText("B")
        self._bold_btn.setCheckable(True)
        self._bold_btn.setToolTip("Bold")
        self._bold_btn.toggled.connect(self.bold_changed.emit)
        layout.addWidget(self._bold_btn)

        self._italic_btn = QToolButton()
        self._italic_btn.setText("I")
        self._italic_btn.setCheckable(True)
        self._italic_btn.setToolTip("Italic")
        self._italic_btn.toggled.connect(self.italic_changed.emit)
        layout.addWidget(self._italic_btn)

        self._underline_btn = QToolButton()
        self._underline_btn.setText("U")
        self._underline_btn.setCheckable(True)
        self._underline_btn.setToolTip("Underline")
        self._underline_btn.toggled.connect(self.underline_changed.emit)
        layout.addWidget(self._underline_btn)

        self._strikeout_btn = QToolButton()
        self._strikeout_btn.setText("S")
        self._strikeout_btn.setCheckable(True)
        self._strikeout_btn.setToolTip("Strikeout")
        self._strikeout_btn.toggled.connect(self.strikeout_changed.emit)
        layout.addWidget(self._strikeout_btn)

        self._color_btn = QToolButton()
        self._color_btn.setText("A")
        self._color_btn.setToolTip("Text Color")
        self._color_btn.setStyleSheet("background-color: black; min-width: 24px; min-height: 24px;")
        self._color_btn.clicked.connect(self._pick_color)
        layout.addWidget(self._color_btn)

        self._bg_transparent = QCheckBox("Transparent")
        self._bg_transparent.setChecked(True)
        self._bg_transparent.toggled.connect(
            lambda checked: self.background_mode_changed.emit(
                "transparent" if checked else "opaque"
            )
        )
        layout.addWidget(self._bg_transparent)

    def _on_font_changed(self) -> None:
        font = QFont(self._font_combo.currentText(), self._size_spin.value())
        self.font_changed.emit(font)

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(0, 0, 0), self, "Text Color")
        if color.isValid():
            self._color_btn.setStyleSheet(
                f"background-color: {color.name()}; min-width: 24px; min-height: 24px;"
            )
            self.color_changed.emit(color)
