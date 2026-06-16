from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import (
    QCursor,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QWheelEvent,
)


class BaseTool(QObject):
    def __init__(self, canvas_widget):
        super().__init__()
        self.canvas = canvas_widget
        self._active = False
        self._start_pos = None
        self._current_pos = None

    def name(self) -> str:
        raise NotImplementedError

    def activate(self) -> None:
        self._active = True
        self.canvas.setCursor(self.cursor())

    def deactivate(self) -> None:
        self._active = False

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    def mouse_press_event(self, event: QMouseEvent) -> None:
        self._start_pos = self.canvas.map_scene_to_image(event.position().toPoint())
        self._current_pos = self._start_pos

    def mouse_move_event(self, event: QMouseEvent) -> None:
        self._current_pos = self.canvas.map_scene_to_image(event.position().toPoint())

    def mouse_release_event(self, event: QMouseEvent) -> None:
        self._start_pos = None
        self._current_pos = None

    def key_press_event(self, event: QKeyEvent) -> None:
        pass

    def key_release_event(self, event: QKeyEvent) -> None:
        pass

    def wheel_event(self, event: QWheelEvent) -> None:
        pass

    def paint_overlay(self, painter: QPainter) -> None:
        pass
