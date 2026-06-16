from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import (
    QColor,
    QCursor,
    QMouseEvent,
    QPainter,
    QPen,
)

from .base_tool import BaseTool


class PencilTool(BaseTool):
    def __init__(self, canvas_widget):
        super().__init__(canvas_widget)
        self._size = 1
        self._last_point = None
        self._drawing = False

    def name(self) -> str:
        return "Pencil"

    def cursor(self) -> QCursor:
        if self._size <= 3:
            return QCursor(Qt.CursorShape.CrossCursor)
        return QCursor(Qt.CursorShape.CrossCursor)

    def set_size(self, size: int) -> None:
        self._size = max(1, size)

    def mouse_press_event(self, event: QMouseEvent) -> None:
        super().mouse_press_event(event)
        if event.button() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            return
        self._drawing = True
        self._last_point = self.canvas.map_scene_to_image(event.position().toPoint())
        color = self._get_color(event)
        self._draw_point(self._last_point, color)

    def mouse_move_event(self, event: QMouseEvent) -> None:
        super().mouse_move_event(event)
        if not self._drawing:
            return
        current = self.canvas.map_scene_to_image(event.position().toPoint())
        color = self._get_color(event)
        self._draw_line(self._last_point, current, color)
        self._last_point = current

    def mouse_release_event(self, event: QMouseEvent) -> None:
        if self._drawing:
            self._drawing = False
            self._last_point = None
            self.canvas.commit_drawing()
        super().mouse_release_event(event)

    def _get_color(self, event: QMouseEvent) -> QColor:
        if event.button() == Qt.MouseButton.RightButton:
            return QColor(self.canvas.color2)
        return QColor(self.canvas.color1)

    def _draw_point(self, pos: QPoint, color: QColor) -> None:
        painter = QPainter(self.canvas.preview_pixmap)
        painter.setPen(
            QPen(
                color,
                self._size,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.drawPoint(pos)
        painter.end()
        self.canvas.update_preview()

    def _draw_line(self, p1: QPoint, p2: QPoint, color: QColor) -> None:
        if p1 == p2:
            self._draw_point(p1, color)
            return
        painter = QPainter(self.canvas.preview_pixmap)
        painter.setPen(
            QPen(
                color,
                self._size,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.drawLine(p1, p2)
        painter.end()
        self.canvas.update_preview()
