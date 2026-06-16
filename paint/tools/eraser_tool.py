from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import (
    QCursor,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
)

from .base_tool import BaseTool


class EraserTool(BaseTool):
    def __init__(self, canvas_widget):
        super().__init__(canvas_widget)
        self._size = 8
        self._last_point = None
        self._drawing = False

    def name(self) -> str:
        return "Eraser"

    def cursor(self) -> QCursor:
        pixmap = QPixmap(QSize(self._size, self._size))
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(0, 0, self._size - 1, self._size - 1)
        painter.end()
        return QCursor(pixmap)

    def set_size(self, size: int) -> None:
        self._size = max(1, size)
        if self._active:
            self.canvas.setCursor(self.cursor())

    def mouse_press_event(self, event: QMouseEvent) -> None:
        super().mouse_press_event(event)
        if event.button() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            return
        self._drawing = True
        self._last_point = self.canvas.map_scene_to_image(event.position().toPoint())
        self._erase_at(self._last_point)

    def mouse_move_event(self, event: QMouseEvent) -> None:
        super().mouse_move_event(event)
        if not self._drawing:
            return
        current = self.canvas.map_scene_to_image(event.position().toPoint())
        self._erase_line(self._last_point, current)
        self._last_point = current

    def mouse_release_event(self, event: QMouseEvent) -> None:
        if self._drawing:
            self._drawing = False
            self._last_point = None
            self.canvas.commit_drawing()
        super().mouse_release_event(event)

    def _erase_at(self, pos: QPoint) -> None:
        painter = QPainter(self.canvas.preview_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.BrushStyle.SolidPattern)
        r = self._size // 2
        painter.drawRect(pos.x() - r, pos.y() - r, self._size, self._size)
        painter.end()
        self.canvas.update_preview()

    def _erase_line(self, p1: QPoint, p2: QPoint) -> None:
        painter = QPainter(self.canvas.preview_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        pen = QPen(
            Qt.GlobalColor.transparent,
            self._size,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        painter.drawLine(p1, p2)
        painter.end()
        self.canvas.update_preview()
