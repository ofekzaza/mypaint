from PySide6.QtCore import QPoint, QRect, QSize, Qt
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
        self._has_drawn = False

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
        self._has_drawn = False
        self._last_point = self.canvas.map_scene_to_image(event.position().toPoint())

    def mouse_move_event(self, event: QMouseEvent) -> None:
        super().mouse_move_event(event)
        if not self._drawing:
            return
        current = self.canvas.map_scene_to_image(event.position().toPoint())
        if not self._has_drawn:
            self.canvas._undo.push_state(self.canvas.image().copy())
            self._has_drawn = True
            self._erase_at(self._last_point)
        self._erase_line(self._last_point, current)
        self._last_point = current

    def mouse_release_event(self, event: QMouseEvent) -> None:
        if self._drawing:
            self._drawing = False
            self._last_point = None
            if self._has_drawn:
                self.canvas.update_image_item()
                self.canvas._dirty = True
            self._has_drawn = False
        super().mouse_release_event(event)

    def _erase_at(self, pos: QPoint) -> None:
        painter = QPainter(self.canvas.image())
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        r = self._size // 2
        painter.fillRect(QRect(pos.x() - r, pos.y() - r, self._size, self._size), Qt.GlobalColor.white)
        painter.end()
        self.canvas.update_image_item()

    def _erase_line(self, p1: QPoint, p2: QPoint) -> None:
        painter = QPainter(self.canvas.image())
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        pen = QPen(
            Qt.GlobalColor.white,
            self._size,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        painter.drawLine(p1, p2)
        painter.end()
        self.canvas.update_image_item()
