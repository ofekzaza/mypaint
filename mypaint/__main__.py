import os
import sys

from mypaint.app import create_app
from mypaint.main_window import MainWindow


def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "wayland")
    app = create_app()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
