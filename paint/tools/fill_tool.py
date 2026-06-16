import struct

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QCursor, QImage, QMouseEvent

from .base_tool import BaseTool


class FloodFillWorker(QThread):
    finished = Signal(QImage)
    progress = Signal(int)

    def __init__(
        self, image: QImage, start_x: int, start_y: int, fill_color: QColor, tolerance: int = 0
    ):
        super().__init__()
        self._image = image.convertToFormat(QImage.Format.Format_ARGB32)
        self._start_x = start_x
        self._start_y = start_y
        self._fill_color = fill_color.rgba()
        self._tolerance = tolerance
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        w = self._image.width()
        h = self._image.height()
        bpl = self._image.bytesPerLine()

        data = bytearray(self._image.constBits())
        get_pixel = lambda x, y: struct.unpack_from(
            "<I", data, y * bpl + x * 4
        )[0]
        set_pixel = lambda x, y, c: struct.pack_into(
            "<I", data, y * bpl + x * 4, c
        )

        target = get_pixel(self._start_x, self._start_y)

        if target == self._fill_color:
            self.finished.emit(self._image)
            return

        stack = [(self._start_x, self._start_y)]
        total_pixels = w * h

        while stack and not self._cancelled:
            cx, cy = stack.pop()
            if cx < 0 or cx >= w or cy < 0 or cy >= h:
                continue

            current = get_pixel(cx, cy)
            if not self._pixel_equal(current, target):
                continue

            set_pixel(cx, cy, self._fill_color)

            stack.append((cx + 1, cy))
            stack.append((cx - 1, cy))
            stack.append((cx, cy + 1))
            stack.append((cx, cy - 1))

        if not self._cancelled:
            result = QImage(
                data, w, h, bpl, QImage.Format.Format_ARGB32
            )
            self.finished.emit(result)

    def _pixel_equal(self, a: int, b: int) -> bool:
        if self._tolerance == 0:
            return a == b
        ra = a & 0xFF
        ga = (a >> 8) & 0xFF
        ba = (a >> 16) & 0xFF
        rb = b & 0xFF
        gb = (b >> 8) & 0xFF
        bb = (b >> 16) & 0xFF
        return (
            abs(ra - rb) <= self._tolerance
            and abs(ga - gb) <= self._tolerance
            and abs(ba - bb) <= self._tolerance
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
        if x < 0 or x >= self.canvas.image().width() or y < 0 or y >= self.canvas.image().height():
            return

        source = self.canvas.image().pixelColor(x, y)
        if source == color:
            return

        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()

        image = self.canvas.image().copy()
        self._worker = FloodFillWorker(image, x, y, color)
        self._worker.finished.connect(self._on_fill_finished)
        self._worker.start()

    def _on_fill_finished(self, result: QImage) -> None:
        self.canvas.apply_image(result)
