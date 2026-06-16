from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


class ThemeService:
    def __init__(self):
        self._app = QApplication.instance()

    def is_dark_mode(self) -> bool:
        palette = self._app.palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        return window_color.lightness() < 128

    def workspace_color(self):
        return QColor(Qt.GlobalColor.white)

    def canvas_background(self):
        if self.is_dark_mode():
            return QColor(60, 60, 60)
        return QColor(200, 200, 200)

    def accent_color(self):
        palette = self._app.palette()
        return palette.color(QPalette.ColorRole.Highlight)
