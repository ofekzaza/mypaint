from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class Ruler(QWidget):
    def __init__(self, orientation: Qt.Orientation, parent=None):
        super().__init__(parent)
        self._orientation = orientation
        self._offset = 0
        self._scale = 1.0
        self._length = 0
        self.setMinimumSize(20, 20)

    def set_params(self, offset: float, scale: float, length: int) -> None:
        self._offset = offset
        self._scale = scale
        self._length = length
        self.update()

    def minimumSizeHint(self) -> QSize:
        return QSize(20, 20)

    def sizeHint(self) -> QSize:
        return QSize(200, 20) if self._orientation == Qt.Orientation.Horizontal else QSize(20, 200)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), QColor(240, 240, 240))
        painter.setPen(QPen(QColor(128, 128, 128), 1))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        tick_length = 3
        sub_ticks = 5
        major_interval = 50 * self._scale
        if major_interval < 20:
            major_interval = 20 * self._scale
        if major_interval < 5:
            return

        step = max(1, int(major_interval / sub_ticks))

        painter.setPen(QPen(QColor(80, 80, 80), 1))

        if self._orientation == Qt.Orientation.Horizontal:
            end = min(self._length, self.width())
            x = int(-self._offset % step)
            while x < end:
                val = int((x + self._offset) / step) * step
                if val % int(major_interval) == 0 and val > 0:
                    painter.drawLine(x, self.height(), x, self.height() - tick_length - 5)
                    painter.setFont(QFont("Sans", 7))
                    painter.drawText(x + 2, 10, str(int(val / self._scale)))
                    painter.setPen(QPen(QColor(80, 80, 80), 1))
                else:
                    painter.drawLine(x, self.height(), x, self.height() - tick_length)
                x += step
        else:
            end = min(self._length, self.height())
            y = int(-self._offset % step)
            while y < end:
                val = int((y + self._offset) / step) * step
                if val % int(major_interval) == 0 and val > 0:
                    painter.drawLine(self.width(), y, self.width() - tick_length - 5, y)
                    painter.setFont(QFont("Sans", 7))
                    painter.save()
                    painter.translate(12, y + 2)
                    painter.rotate(-90)
                    painter.drawText(0, 0, str(int(val / self._scale)))
                    painter.restore()
                    painter.setPen(QPen(QColor(80, 80, 80), 1))
                else:
                    painter.drawLine(self.width(), y, self.width() - tick_length, y)
                y += step


class HRuler(Ruler):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)


class VRuler(Ruler):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Vertical, parent)
