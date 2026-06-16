import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


def create_app() -> QApplication:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Paint")
    app.setOrganizationName("Omarchy")
    app.setStyle("Fusion")

    return app
