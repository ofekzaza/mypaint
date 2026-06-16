from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QMouseEvent

from .base_tool import BaseTool


class MagnifierTool(BaseTool):
    def name(self) -> str:
        return "Magnifier"

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    def mouse_press_event(self, event: QMouseEvent) -> None:
        super().mouse_press_event(event)
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = event.position().toPoint()
            self.canvas.zoom_centered(scene_pos)
