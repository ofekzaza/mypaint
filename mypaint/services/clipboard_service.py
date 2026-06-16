import subprocess

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication


class ClipboardService:
    def __init__(self):
        self._clipboard = QApplication.clipboard()
        self._wayland_fallback = False

    def copy_image(self, image: QImage) -> bool:
        success = self._clipboard.setImage(image)
        if not success:
            self._wayland_copy_fallback(image)
        return True

    def paste_image(self) -> QImage | None:
        mime = self._clipboard.mimeData()
        if mime.hasImage():
            return self._clipboard.image()
        if self._wayland_fallback:
            return self._wayland_paste_fallback()
        return None

    def _wayland_copy_fallback(self, image: QImage) -> None:
        try:
            byte_array = QByteArray()
            from PySide6.QtCore import QBuffer

            buffer = QBuffer(byte_array)
            buffer.open(QBuffer.OpenModeFlag.WriteOnly)
            image.save(buffer, "PNG")
            buffer.close()
            proc = subprocess.Popen(
                ["wl-copy", "--type", "image/png"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            proc.communicate(input=bytes(byte_array.data()))
            self._wayland_fallback = True
        except FileNotFoundError:
            pass

    def _wayland_paste_fallback(self) -> QImage | None:
        try:
            result = subprocess.run(
                ["wl-paste", "--no-newline"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout:
                image = QImage()
                image.loadFromData(result.stdout)
                if not image.isNull():
                    return image
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None

    def has_image(self) -> bool:
        mime = self._clipboard.mimeData()
        if mime.hasImage():
            return True
        return False
