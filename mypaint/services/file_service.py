import os
from PySide6.QtCore import QBuffer, QByteArray, QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QFileDialog, QMessageBox

SUPPORTED_OPEN_FORMATS = [
    "PNG (*.png)",
    "BMP (*.bmp)",
    "JPEG (*.jpg *.jpeg)",
    "SVG (*.svg)",
    "All Images (*.png *.bmp *.jpg *.jpeg *.svg)",
]

SUPPORTED_SAVE_FORMATS: dict[str, str] = {
    "PNG (*.png)": "png",
    "BMP (*.bmp)": "bmp",
    "JPEG (*.jpg *.jpeg)": "jpg",
}

# Map from format extension to the preferred filter key
EXT_TO_FILTER: dict[str, str] = {
    "png": "PNG (*.png)",
    "bmp": "BMP (*.bmp)",
    "jpg": "JPEG (*.jpg *.jpeg)",
    "jpeg": "JPEG (*.jpg *.jpeg)",
    "svg": "SVG (*.svg)",
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

        if file_path.lower().endswith(".svg"):
            return FileService._load_svg(file_path, parent)

        image = QImage(file_path)
        if image.isNull():
            QMessageBox.warning(parent, "Error", f"Could not load image: {file_path}")
            return None
        return image

    @staticmethod
    def _load_svg(file_path: str, parent=None) -> QImage | None:
        renderer = QSvgRenderer(file_path)
        if not renderer.isValid():
            QMessageBox.warning(parent, "Error", f"Could not load SVG: {file_path}")
            return None
        size = renderer.defaultSize()
        if size.isEmpty() or size.width() <= 0 or size.height() <= 0:
            size = QSize(800, 600)
        image = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
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
            ext = "." + img_format
            if not file_path.lower().endswith(ext):
                file_path += ext
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
