from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QImage,
    QMouseEvent,
)

from .base_tool import BaseTool


class FloodFillWorker(QThread):
    finished = Signal(QImage)
    progress = Signal(int)

    def __init__(
        self, image: QImage, start_x: int, start_y: int, fill_color: QColor, tolerance: int = 0
    ):
        super().__init__()
        self._image = image.copy()
        self._start_x = start_x
        self._start_y = start_y
        self._fill_color = fill_color
        self._tolerance = tolerance
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        target = self._image.pixelColor(self._start_x, self._start_y)
        if self._color_equal(target, self._fill_color):
            self.finished.emit(self._image)
            return

        w, h = self._image.width(), self._image.height()
        stack = [(self._start_x, self._start_y)]
        processed = 0
        total_pixels = w * h

        while stack and not self._cancelled:
            cx, cy = stack.pop()
            if cx < 0 or cx >= w or cy < 0 or cy >= h:
                continue

            current = self._image.pixelColor(cx, cy)
            if not self._color_equal(current, target):
                continue

            self._image.setPixelColor(cx, cy, self._fill_color)

            stack.append((cx + 1, cy))
            stack.append((cx - 1, cy))
            stack.append((cx, cy + 1))
            stack.append((cx, cy - 1))

            processed += 1
            if processed % 1000 == 0:
                self.progress.emit(int(processed * 100 / max(total_pixels, 1)))

        if not self._cancelled:
            self.finished.emit(self._image)

    def _color_equal(self, a: QColor, b: QColor) -> bool:
        if self._tolerance == 0:
            return a == b
        return (
            abs(a.red() - b.red()) <= self._tolerance
            and abs(a.green() - b.green()) <= self._tolerance
            and abs(a.blue() - b.blue()) <= self._tolerance
        )


class FillTool(BaseTool):
    def __init__(self, canvas_widget):
        super().__init__(canvas_widget)
        self._worker: FloodFillWorker | None = None

    def name(self) -> str:
        return "Fill"

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    def mouse_press_event(self, event: QMouseEvent) -> None:
        super().mouse_press_event(event)
        if event.button() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            return

        pos = self.canvas.map_scene_to_image(event.position().toPoint())
        color = (
            QColor(self.canvas.color2)
            if event.button() == Qt.MouseButton.RightButton
            else QColor(self.canvas.color1)
        )

        self._start_fill(pos.x(), pos.y(), color)

    def _start_fill(self, x: int, y: int, color: QColor) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()

        image = self.canvas.image().copy()
        self._worker = FloodFillWorker(image, x, y, color)
        self._worker.finished.connect(self._on_fill_finished)
        self._worker.start()

    def _on_fill_finished(self, result: QImage) -> None:
        self.canvas.set_image_direct(result)
        self.canvas.commit_drawing()
