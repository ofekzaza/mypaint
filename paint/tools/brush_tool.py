import math
import random

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QMouseEvent,
    QPainter,
    QPen,
)

from .base_tool import BaseTool

BRUSH_ROUND = "round"
BRUSH_MARKER = "marker"
BRUSH_AIRBRUSH = "airbrush"


class BrushTool(BaseTool):
    def __init__(self, canvas_widget):
        super().__init__(canvas_widget)
        self._size = 5
        self._brush_type = BRUSH_ROUND
        self._airbrush_density = 30
        self._airbrush_radius = 20
        self._last_point = None
        self._drawing = False
        self._spray_particles: list[QPoint] = []

    def name(self) -> str:
        return "Brush"

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    def set_size(self, size: int) -> None:
        self._size = max(1, size)
        self._airbrush_radius = max(5, size * 2)

    def set_brush_type(self, brush_type: str) -> None:
        self._brush_type = brush_type

    def mouse_press_event(self, event: QMouseEvent) -> None:
        super().mouse_press_event(event)
        if event.button() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            return
        self._drawing = True
        self._last_point = self.canvas.map_scene_to_image(event.position().toPoint())
        color = self._get_color(event)
        self._apply_brush(self._last_point, color)

    def mouse_move_event(self, event: QMouseEvent) -> None:
        super().mouse_move_event(event)
        if not self._drawing:
            return
        current = self.canvas.map_scene_to_image(event.position().toPoint())
        color = self._get_color(event)
        self._apply_brush_stroke(self._last_point, current, color)
        self._last_point = current

    def mouse_release_event(self, event: QMouseEvent) -> None:
        if self._drawing:
            self._drawing = False
            self._last_point = None
            self._spray_particles.clear()
            self.canvas.commit_drawing()
        super().mouse_release_event(event)

    def _get_color(self, event: QMouseEvent) -> QColor:
        if event.button() == Qt.MouseButton.RightButton:
            return QColor(self.canvas.color2)
        return QColor(self.canvas.color1)

    def _apply_brush(self, pos: QPoint, color: QColor) -> None:
        painter = QPainter(self.canvas.preview_pixmap)

        if self._brush_type == BRUSH_ROUND:
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            r = self._size / 2.0
            painter.drawEllipse(QPointF(pos), r, r)

        elif self._brush_type == BRUSH_MARKER:
            pen = QPen(color, 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(QBrush(color))
            r = self._size / 2.0
            painter.drawEllipse(QPointF(pos), r, r)

        elif self._brush_type == BRUSH_AIRBRUSH:
            self._spray(pos, color, painter)

        painter.end()
        self.canvas.update_preview()

    def _apply_brush_stroke(self, p1: QPoint, p2: QPoint, color: QColor) -> None:
        painter = QPainter(self.canvas.preview_pixmap)

        if self._brush_type in (BRUSH_ROUND, BRUSH_MARKER):
            pen = QPen(
                QBrush(color),
                self._size,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
            painter.setPen(pen)
            if self._brush_type == BRUSH_ROUND:
                painter.setBrush(Qt.BrushStyle.NoBrush)
            else:
                painter.setBrush(QBrush(color))
            painter.drawLine(p1, p2)

        elif self._brush_type == BRUSH_AIRBRUSH:
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            dist = math.sqrt(dx * dx + dy * dy)
            steps = max(int(dist / 2.0), 1)
            for i in range(steps + 1):
                t = i / steps
                x = int(p1.x() + dx * t)
                y = int(p1.y() + dy * t)
                self._spray(QPoint(x, y), color, painter)

        painter.end()
        self.canvas.update_preview()

    def _spray(self, pos: QPoint, color: QColor, painter: QPainter) -> None:
        density = self._airbrush_density
        radius = self._airbrush_radius
        pen = QPen(QColor(color.red(), color.green(), color.blue(), 160), 1, Qt.PenStyle.SolidLine)
        painter.setPen(pen)

        for _ in range(density):
            angle = random.uniform(0, 2 * math.pi)
            r = random.uniform(0, radius)
            x = int(pos.x() + r * math.cos(angle))
            y = int(pos.y() + r * math.sin(angle))
            painter.drawPoint(x, y)
