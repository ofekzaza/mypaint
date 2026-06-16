from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QImage, QPainter, Qt, QTransform


class ImageBuffer:
    def __init__(self, width: int = 800, height: int = 600):
        self._image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        self._image.fill(Qt.GlobalColor.white)

    @property
    def image(self) -> QImage:
        return self._image

    @image.setter
    def image(self, new_image: QImage) -> None:
        self._image = new_image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)

    def width(self) -> int:
        return self._image.width()

    def height(self) -> int:
        return self._image.height()

    def size(self):
        return self._image.size()

    def rect(self) -> QRect:
        return self._image.rect()

    def clear(self, color: QColor = Qt.GlobalColor.white) -> None:
        self._image.fill(color)

    def resize(
        self, new_width: int, new_height: int, expand_color: QColor = Qt.GlobalColor.white
    ) -> None:
        new_image = QImage(new_width, new_height, QImage.Format.Format_ARGB32_Premultiplied)
        new_image.fill(expand_color)
        painter = QPainter(new_image)
        painter.drawImage(0, 0, self._image)
        painter.end()
        self._image = new_image

    def copy(self) -> QImage:
        return self._image.copy()

    def crop(self, rect: QRect) -> None:
        self._image = self._image.copy(rect)

    def rotate_cw(self) -> None:
        transform = self._image.transformed(
            QTransform().rotate(90), Qt.TransformationMode.SmoothTransformation
        )
        self._image = transform

    def rotate_ccw(self) -> None:
        transform = self._image.transformed(
            QTransform().rotate(-90), Qt.TransformationMode.SmoothTransformation
        )
        self._image = transform

    def rotate_180(self) -> None:
        transform = self._image.transformed(
            QTransform().rotate(180), Qt.TransformationMode.SmoothTransformation
        )
        self._image = transform

    def flip_horizontal(self) -> None:
        self._image = self._image.mirrored(True, False)

    def flip_vertical(self) -> None:
        self._image = self._image.mirrored(False, True)

    def draw_image(self, painter: QPainter, rect: QRect | None = None) -> None:
        if rect:
            painter.drawImage(rect, self._image)
        else:
            painter.drawImage(0, 0, self._image)
