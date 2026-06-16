from PySide6.QtCore import QEvent, QRect, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QColorDialog, QFrame, QHBoxLayout, QToolButton, QVBoxLayout, QWidget

DEFAULT_COLORS = [
    QColor(0, 0, 0),
    QColor(128, 128, 128),
    QColor(192, 192, 192),
    QColor(255, 255, 255),
    QColor(128, 0, 0),
    QColor(255, 0, 0),
    QColor(255, 128, 128),
    QColor(128, 128, 0),
    QColor(255, 255, 0),
    QColor(0, 128, 0),
    QColor(0, 255, 0),
    QColor(128, 255, 128),
    QColor(0, 128, 128),
    QColor(0, 255, 255),
    QColor(128, 255, 255),
    QColor(0, 0, 128),
    QColor(0, 0, 255),
    QColor(128, 128, 255),
    QColor(128, 0, 128),
    QColor(255, 0, 255),
    QColor(255, 128, 255),
    QColor(128, 64, 0),
    QColor(255, 128, 0),
    QColor(255, 192, 128),
    QColor(64, 128, 64),
    QColor(64, 64, 128),
    QColor(192, 128, 64),
]

SWATCH_SIZE = 20
SWATCH_MARGIN = 2


class ColorSwatch(QWidget):
    clicked = Signal(QColor, Qt.MouseButton)

    def __init__(self, color: QColor, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(SWATCH_SIZE, SWATCH_SIZE)
        self.setToolTip(color.name())

    def set_color(self, color: QColor) -> None:
        self._color = color
        self.setToolTip(color.name())
        self.update()

    def color(self) -> QColor:
        return self._color

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), self._color)
        painter.setPen(Qt.GlobalColor.gray)
        painter.drawRect(QRect(0, 0, self.width() - 1, self.height() - 1))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.clicked.emit(self._color, event.button())


class ColorPalette(QFrame):
    color1_changed = Signal(QColor)
    color2_changed = Signal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color1 = QColor(0, 0, 0)
        self._color2 = QColor(255, 255, 255)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        indicators = QVBoxLayout()
        indicators.setSpacing(2)

        self._color1_preview = ColorSwatch(self._color1)
        self._color1_preview.setFixedSize(28, 28)
        self._color1_preview.clicked.connect(lambda c, b: self._on_edit_colors(False))
        indicators.addWidget(self._color1_preview)

        self._color2_preview = ColorSwatch(self._color2)
        self._color2_preview.setFixedSize(28, 28)
        self._color2_preview.clicked.connect(lambda c, b: self._on_edit_colors(True))
        indicators.addWidget(self._color2_preview)

        layout.addLayout(indicators)

        swatch_vbox = QVBoxLayout()
        swatch_vbox.setSpacing(SWATCH_MARGIN)
        swatch_vbox.setContentsMargins(0, 0, 0, 0)

        n_cols = 9
        for row_start in range(0, len(DEFAULT_COLORS), n_cols):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(SWATCH_MARGIN)
            row_layout.setContentsMargins(0, 0, 0, 0)
            for color in DEFAULT_COLORS[row_start : row_start + n_cols]:
                swatch = ColorSwatch(color)
                swatch.clicked.connect(self._on_swatch_clicked)
                row_layout.addWidget(swatch)
            swatch_vbox.addLayout(row_layout)

        layout.addLayout(swatch_vbox)

        self._edit_colors_btn = QToolButton()
        self._edit_colors_btn.setText("Edit\nColors")
        self._edit_colors_btn.setToolTip("Left-click: edit color 1 | Right-click: edit color 2")
        self._edit_colors_btn.clicked.connect(lambda: self._on_edit_colors(False))
        self._edit_colors_btn.installEventFilter(self)
        layout.addWidget(self._edit_colors_btn)

    @property
    def color1(self) -> QColor:
        return self._color1

    @color1.setter
    def color1(self, color: QColor) -> None:
        new_c = QColor(color)
        if self._color1 == new_c:
            return
        self._color1 = new_c
        self._color1_preview.set_color(self._color1)
        self.color1_changed.emit(self._color1)

    @property
    def color2(self) -> QColor:
        return self._color2

    @color2.setter
    def color2(self, color: QColor) -> None:
        new_c = QColor(color)
        if self._color2 == new_c:
            return
        self._color2 = new_c
        self._color2_preview.set_color(self._color2)
        self.color2_changed.emit(self._color2)

    def _on_swatch_clicked(self, color: QColor, button: Qt.MouseButton) -> None:
        if button == Qt.MouseButton.LeftButton:
            self.color1 = color
        elif button == Qt.MouseButton.RightButton:
            self.color2 = color

    def _on_edit_colors(self, edit_color2: bool = False) -> None:
        initial = self._color2 if edit_color2 else self._color1
        dialog = QColorDialog(initial, self)
        if dialog.exec():
            if edit_color2:
                self.color2 = dialog.currentColor()
            else:
                self.color1 = dialog.currentColor()

    def eventFilter(self, obj, event) -> bool:
        if obj is self._edit_colors_btn and event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.RightButton:
                self._on_edit_colors(True)
                return True
        return super().eventFilter(obj, event)
