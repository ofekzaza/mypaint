from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QMouseEvent

from .base_tool import BaseTool


class ColorPickerTool(BaseTool):
    def name(self) -> str:
        return "Color Picker"

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    def mouse_press_event(self, event: QMouseEvent) -> None:
        super().mouse_press_event(event)
        pos = self.canvas.map_scene_to_image(event.position().toPoint())
        color = self.canvas.image().pixelColor(pos)

        if event.button() == Qt.MouseButton.RightButton:
            self.canvas.color2 = color
        else:
            self.canvas.color1 = color
