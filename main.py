import os
import sys


def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "wayland")


from mypaint.app import create_app
from mypaint.main_window import MainWindow

app = create_app()
window = MainWindow()
window.show()
sys.exit(app.exec())


if __name__ == "__main__":
    main()
