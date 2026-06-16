from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QGridLayout, QToolButton

TOOL_NAMES = [
    "select_rect",
    "select_freeform",
    "pencil",
    "brush",
    "eraser",
    "fill",
    "picker",
    "magnifier",
    "text",
    "line",
    "curve",
    "rectangle",
    "ellipse",
    "rounded_rect",
    "polygon",
    "arrow_right",
    "arrow_left",
    "arrow_up",
    "arrow_down",
]

TOOL_LABELS = {
    "pencil": "Pencil",
    "brush": "Brush",
    "eraser": "Eraser",
    "fill": "Fill with color",
    "picker": "Pick color",
    "magnifier": "Magnifier",
    "text": "Text",
    "line": "Line",
    "curve": "Curve",
    "rectangle": "Rectangle",
    "ellipse": "Ellipse",
    "rounded_rect": "Rounded Rectangle",
    "polygon": "Polygon",
    "arrow_right": "Arrow \u2192",
    "arrow_left": "Arrow \u2190",
    "arrow_up": "Arrow \u2191",
    "arrow_down": "Arrow \u2193",
    "select_rect": "Rectangular selection",
    "select_freeform": "Free-form selection",
}

TOOLS_PER_ROW = 7


def _render_tool_icon(tool_name: str, size: int = 24) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(80, 80, 80), 1.5)
    painter.setPen(pen)
    brush = QColor(60, 60, 60)

    cx, cy = size // 2, size // 2
    s4, s8, s3 = size // 4, size // 8, size // 3

    if tool_name == "pencil":
        body = QPainterPath()
        body.moveTo(cx - s4, cy + s4)
        body.lineTo(cx - s4 + 4, cy + s4 + 3)
        body.lineTo(cx + s4 + 1, cy - s4 + 2)
        body.lineTo(cx + s4 - 1, cy - s4)
        body.closeSubpath()
        painter.setBrush(QColor(220, 180, 60))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(body)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        body2 = QPainterPath()
        body2.moveTo(cx - s4, cy + s4)
        body2.lineTo(cx - s4 + 4, cy + s4 + 3)
        body2.lineTo(cx + s4 + 1, cy - s4 + 2)
        body2.lineTo(cx + s4 - 1, cy - s4)
        body2.closeSubpath()
        painter.drawPath(body2)
        tip = QPainterPath()
        tip.moveTo(cx + s4, cy - s4)
        tip.lineTo(cx + s4 + 4, cy - s4 + 2)
        tip.lineTo(cx + s4 + 1, cy - s4 + 4)
        tip.closeSubpath()
        painter.setBrush(QColor(60, 60, 60))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(tip)
    elif tool_name == "brush":
        painter.setBrush(brush)
        painter.drawEllipse(cx - s4, cy - s4, size // 2, size // 2)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(cx, cy + s4, cx, cy + s4 + s4)
    elif tool_name == "eraser":
        rect = QRect(cx - s4, cy - s4, size // 2, size // 2)
        painter.fillRect(rect, QColor(200, 200, 255))
        painter.drawRect(rect)
    elif tool_name == "fill":
        bucket = QPainterPath()
        bucket.moveTo(cx - s4, cy - s4 + 2)
        bucket.lineTo(cx - s4, cy + s4)
        bucket.lineTo(cx + s4, cy + s4)
        bucket.lineTo(cx + s4, cy - s4 + 2)
        bucket.closeSubpath()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(bucket)
        painter.drawLine(cx - s4, cy - s4 + 2, cx + s4, cy - s4 + 2)
        painter.drawLine(cx - s4, cy - s4 + 2, cx - s4 - 3, cy - s4)
        painter.drawLine(cx + s4, cy - s4 + 2, cx + s4 + 3, cy - s4)
        painter.setBrush(QColor(80, 80, 80))
        painter.setPen(Qt.PenStyle.NoPen)
        for dx in (-2, 0, 2):
            painter.drawRect(cx + dx, cy + s4 - 1, 1, 3)
    elif tool_name == "picker":
        painter.drawLine(cx - s4, cy + s4, cx + s4, cy - s4)
        painter.drawRect(cx + s4 - 2, cy - s4 - 2, 4, 4)
    elif tool_name == "magnifier":
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(cx - s3, cy - s3, s3 * 2, s3 * 2)
        painter.drawLine(cx, cy, cx + s4, cy + s4)
    elif tool_name == "text":
        painter.drawText(
            QRect(cx - s4, cy - s4, size // 2, size // 2),
            Qt.AlignmentFlag.AlignCenter,
            "A",
        )
    elif tool_name == "line":
        painter.drawLine(cx - s4, cy + s4, cx + s4, cy - s4)
    elif tool_name == "curve":
        path = QPainterPath()
        path.moveTo(cx - s4, cy + s4)
        path.cubicTo(cx - s8, cy - s4, cx + s8, cy + s4, cx + s4, cy - s4)
        painter.drawPath(path)
    elif tool_name == "rectangle":
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRect(cx - s4, cy - s4, size // 2, size // 2))
    elif tool_name == "ellipse":
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(cx - s4, cy - s4, size // 2, size // 2)
    elif tool_name == "rounded_rect":
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRect(cx - s4, cy - s4, size // 2, size // 2), 4, 4)
    elif tool_name == "polygon":
        pts = [QPoint(cx - s4, cy + s4), QPoint(cx, cy - s4), QPoint(cx + s4, cy + s4)]
        painter.drawPolygon(pts)
    elif tool_name == "arrow_right":
        path = QPainterPath()
        path.moveTo(cx - s4, cy - 2)
        path.lineTo(cx, cy - 2)
        path.lineTo(cx, cy - s4)
        path.lineTo(cx + s4, cy)
        path.lineTo(cx, cy + s4)
        path.lineTo(cx, cy + 2)
        path.lineTo(cx - s4, cy + 2)
        path.closeSubpath()
        painter.setBrush(QColor(80, 80, 80))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
        painter.setBrush(Qt.BrushStyle.NoBrush)
    elif tool_name == "arrow_left":
        path = QPainterPath()
        path.moveTo(cx + s4, cy - 2)
        path.lineTo(cx - 0, cy - 2)
        path.lineTo(cx - 0, cy - s4)
        path.lineTo(cx - s4, cy)
        path.lineTo(cx - 0, cy + s4)
        path.lineTo(cx - 0, cy + 2)
        path.lineTo(cx + s4, cy + 2)
        path.closeSubpath()
        painter.setBrush(QColor(80, 80, 80))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
        painter.setBrush(Qt.BrushStyle.NoBrush)
    elif tool_name == "arrow_up":
        path = QPainterPath()
        path.moveTo(cx - 2, cy + s4)
        path.lineTo(cx - 2, cy)
        path.lineTo(cx - s4, cy)
        path.lineTo(cx, cy - s4)
        path.lineTo(cx + s4, cy)
        path.lineTo(cx + 2, cy)
        path.lineTo(cx + 2, cy + s4)
        path.closeSubpath()
        painter.setBrush(QColor(80, 80, 80))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
        painter.setBrush(Qt.BrushStyle.NoBrush)
    elif tool_name == "arrow_down":
        path = QPainterPath()
        path.moveTo(cx - 2, cy - s4)
        path.lineTo(cx - 2, cy + 0)
        path.lineTo(cx - s4, cy + 0)
        path.lineTo(cx, cy + s4)
        path.lineTo(cx + s4, cy + 0)
        path.lineTo(cx + 2, cy + 0)
        path.lineTo(cx + 2, cy - s4)
        path.closeSubpath()
        painter.setBrush(QColor(80, 80, 80))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
        painter.setBrush(Qt.BrushStyle.NoBrush)
    elif tool_name == "select_rect":
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(80, 80, 80), 1, Qt.PenStyle.DashLine))
        painter.drawRect(QRect(cx - s4, cy - s4, size // 2, size // 2))
    elif tool_name == "select_freeform":
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(80, 80, 80), 1, Qt.PenStyle.DashLine))
        path = [
            (cx - s4, cy - s8),
            (cx - s8, cy - s4),
            (cx + s8, cy - s4),
            (cx + s4, cy),
            (cx + s8, cy + s4),
            (cx - s4, cy + s4),
        ]
        for i in range(len(path) - 1):
            painter.drawLine(path[i][0], path[i][1], path[i + 1][0], path[i + 1][1])

    painter.end()
    return QIcon(pixmap)


class ToolButton(QToolButton):
    def __init__(self, tool_name: str, parent=None):
        super().__init__(parent)
        self._tool_name = tool_name
        self.setCheckable(True)
        self.setIcon(_render_tool_icon(tool_name))
        self.setToolTip(TOOL_LABELS.get(tool_name, tool_name))
        self.setFixedSize(32, 32)
        self.setIconSize(QSize(20, 20))


class ToolPalette(QFrame):
    tool_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buttons: dict[str, ToolButton] = {}
        self._active_tool = "pencil"
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)

        for i, tool_name in enumerate(TOOL_NAMES):
            row = i // TOOLS_PER_ROW
            col = i % TOOLS_PER_ROW
            btn = ToolButton(tool_name)
            btn.clicked.connect(lambda checked, n=tool_name: self._select_tool(n))
            self._buttons[tool_name] = btn
            layout.addWidget(btn, row, col)

        self._buttons[self._active_tool].setChecked(True)

    def _select_tool(self, tool_name: str) -> None:
        if self._active_tool in self._buttons:
            self._buttons[self._active_tool].setChecked(False)
        self._active_tool = tool_name
        self._buttons[tool_name].setChecked(True)
        self.tool_selected.emit(tool_name)

    @property
    def active_tool(self) -> str:
        return self._active_tool

    def set_active_tool(self, tool_name: str) -> None:
        if tool_name in self._buttons:
            self._select_tool(tool_name)
