from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QWidget


class ThumbnailWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thumbnail")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.Dialog)
        self.setFixedSize(256, 256)
        self._image: QImage | None = None
        self._viewport_rect: QRect = QRect()

    def set_image(self, image: QImage) -> None:
        self._image = image
        self.update()

    def set_viewport(self, rect: QRect) -> None:
        self._viewport_rect = rect
        self.update()

    def paintEvent(self, event) -> None:
        if self._image is None or self._image.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        scaled = self._image.scaled(
            self.width(),
            self.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, QPixmap.fromImage(scaled))

        if self._viewport_rect.isValid() and not self._viewport_rect.isEmpty():
            sx = scaled.width() / self._image.width()
            sy = scaled.height() / self._image.height()
            view = QRectF(
                x + self._viewport_rect.x() * sx,
                y + self._viewport_rect.y() * sy,
                self._viewport_rect.width() * sx,
                self._viewport_rect.height() * sy,
            )
            painter.setPen(QColor(255, 0, 0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(view)
