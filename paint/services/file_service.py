from PySide6.QtCore import QBuffer, QByteArray
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QFileDialog, QMessageBox

SUPPORTED_OPEN_FORMATS = [
    "PNG (*.png)",
    "BMP (*.bmp)",
    "JPEG (*.jpg *.jpeg)",
    "All Images (*.png *.bmp *.jpg *.jpeg)",
]

SUPPORTED_SAVE_FORMATS: dict[str, str] = {
    "PNG (*.png)": "png",
    "BMP (*.bmp)": "bmp",
    "JPEG (*.jpg *.jpeg)": "jpg",
}


class FileService:
    @staticmethod
    def open_image(parent=None) -> QImage | None:
        filter_str = ";;".join(SUPPORTED_OPEN_FORMATS)
        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            "Open Image",
            "",
            filter_str,
        )
        if not file_path:
            return None
        image = QImage(file_path)
        if image.isNull():
            QMessageBox.warning(parent, "Error", f"Could not load image: {file_path}")
            return None
        return image

    @staticmethod
    def save_image(
        parent, image: QImage, file_path: str | None = None, format_hint: str | None = None
    ) -> str | None:
        if file_path is None:
            filter_str = ";;".join(SUPPORTED_SAVE_FORMATS.keys())
            file_path, selected_filter = QFileDialog.getSaveFileName(
                parent,
                "Save Image",
                "",
                filter_str,
            )
            if not file_path:
                return None

            img_format = SUPPORTED_SAVE_FORMATS.get(selected_filter, "png")
        else:
            ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "png"
            img_format = format_hint or ext

        result = image.save(file_path, img_format.upper())
        if not result:
            QMessageBox.warning(parent, "Error", f"Could not save image: {file_path}")
            return None
        return file_path

    @staticmethod
    def image_to_bytes(image: QImage, fmt: str = "PNG") -> QByteArray:
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        image.save(buffer, fmt)
        buffer.close()
        return data
