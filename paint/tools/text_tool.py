from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QFontMetrics,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QTextDocument,
)

from .base_tool import BaseTool

HANDLE_SIZE = 8
HANDLE_HALF = HANDLE_SIZE // 2
MIN_BOX_SIZE = 30


class TextTool(BaseTool):
    text_editing = Signal(str)
    editing_started = Signal()
    editing_finished = Signal()

    MODE_NONE = 0
    MODE_CREATE = 1
    MODE_MOVE = 2
    MODE_RESIZE = 3

    def __init__(self, canvas_widget):
        super().__init__(canvas_widget)
        self._mode = self.MODE_NONE
        self._editing = False
        self._rect = QRectF()
        self._text = ""
        self._font = QFont("Sans", 12)
        self._bold = False
        self._italic = False
        self._underline = False
        self._strikeout = False
        self._text_color = QColor(0, 0, 0)
        self._background_mode = "transparent"
        self._background_color = QColor(255, 255, 255)
        self._cursor_pos = 0
        self._resize_handle = -1
        self._drag_offset = QPointF()

    def name(self) -> str:
        return "Text"

    def cursor(self) -> QCursor:
        if self._editing:
            return QCursor(Qt.CursorShape.IBeamCursor)
        return QCursor(Qt.CursorShape.IBeamCursor)

    def _make_font(self) -> QFont:
        f = QFont(self._font)
        f.setBold(self._bold)
        f.setItalic(self._italic)
        f.setUnderline(self._underline)
        f.setStrikeOut(self._strikeout)
        return f

    def set_font(self, font: QFont) -> None:
        self._font = QFont(font)
        self._font.setBold(self._bold)
        self._font.setItalic(self._italic)
        self._font.setUnderline(self._underline)
        self._font.setStrikeOut(self._strikeout)

    def set_bold(self, bold: bool) -> None:
        self._bold = bold

    def set_italic(self, italic: bool) -> None:
        self._italic = italic

    def set_underline(self, underline: bool) -> None:
        self._underline = underline

    def set_strikeout(self, strikeout: bool) -> None:
        self._strikeout = strikeout

    def set_text_color(self, color: QColor) -> None:
        self._text_color = QColor(color)

    def set_background_mode(self, mode: str) -> None:
        self._background_mode = mode

    def set_text(self, text: str) -> None:
        self._text = text
        self._cursor_pos = len(text)

    def text(self) -> str:
        return self._text

    def is_editing(self) -> bool:
        return self._editing

    def commit(self) -> None:
        if not self._editing or not self._rect.isValid() or not self._text:
            self._cancel()
            return

        painter = QPainter(self.canvas.preview_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if self._background_mode == "opaque":
            painter.fillRect(self._rect, self._background_color)

        font = self._make_font()
        painter.setFont(font)
        painter.setPen(QPen(self._text_color))

        doc = QTextDocument(self._text)
        doc.setDefaultFont(font)
        doc.setTextWidth(max(self._rect.width(), 1))

        painter.save()
        painter.translate(self._rect.topLeft())
        clip = QRectF(0, 0, self._rect.width(), self._rect.height())
        painter.setClipRect(clip)
        doc.drawContents(painter)
        painter.restore()
        painter.end()

        self.canvas.commit_drawing()
        self._cancel()

    def _cancel(self) -> None:
        self._editing = False
        self._mode = self.MODE_NONE
        self._rect = QRectF()
        self._text = ""
        self._cursor_pos = 0
        self._resize_handle = -1
        self.canvas.update_preview()
        self.editing_finished.emit()

    def _get_handles(self) -> list[tuple[QPointF, int]]:
        r = self._rect
        return [
            (r.topLeft(), 0),
            (r.topRight(), 1),
            (r.bottomRight(), 2),
            (r.bottomLeft(), 3),
            (QPointF(r.center().x(), r.top()), 4),
            (QPointF(r.right(), r.center().y()), 5),
            (QPointF(r.center().x(), r.bottom()), 6),
            (QPointF(r.left(), r.center().y()), 7),
        ]

    def _handle_at(self, pos: QPointF) -> int:
        for pt, idx in self._get_handles():
            hr = QRectF(pt.x() - HANDLE_HALF, pt.y() - HANDLE_HALF, HANDLE_SIZE, HANDLE_SIZE)
            if hr.contains(pos):
                return idx
        return -1

    def _rect_from_handle(self, handle: int, delta: QPointF) -> QRectF:
        r = QRectF(self._rect)
        if handle == 0:
            r.setTopLeft(r.topLeft() + delta)
        elif handle == 1:
            r.setTopRight(r.topRight() + delta)
        elif handle == 2:
            r.setBottomRight(r.bottomRight() + delta)
        elif handle == 3:
            r.setBottomLeft(r.bottomLeft() + delta)
        elif handle == 4:
            r.setTop(r.top() + delta.y())
        elif handle == 5:
            r.setRight(r.right() + delta.x())
        elif handle == 6:
            r.setBottom(r.bottom() + delta.y())
        elif handle == 7:
            r.setLeft(r.left() + delta.x())
        return r.normalized()

    def _cursor_for_handle(self, handle: int) -> QCursor:
        cursors = {
            0: Qt.CursorShape.SizeFDiagCursor,
            1: Qt.CursorShape.SizeBDiagCursor,
            2: Qt.CursorShape.SizeFDiagCursor,
            3: Qt.CursorShape.SizeBDiagCursor,
            4: Qt.CursorShape.SizeVerCursor,
            5: Qt.CursorShape.SizeHorCursor,
            6: Qt.CursorShape.SizeVerCursor,
            7: Qt.CursorShape.SizeHorCursor,
        }
        return QCursor(cursors.get(handle, Qt.CursorShape.ArrowCursor))

    def _caret_rect(self) -> QRectF:
        font = self._make_font()
        fm = QFontMetrics(font)
        text_before = self._text[: self._cursor_pos]
        lines = text_before.split("\n")
        last_line = lines[-1] if lines else ""
        text_width = fm.horizontalAdvance(last_line)
        line_count = len(lines) - 1
        caret_x = self._rect.x() + text_width
        caret_y = self._rect.y() + (line_count + 1) * fm.height()
        return QRectF(caret_x, caret_y - fm.ascent(), 1, fm.height())

    def mouse_press_event(self, event: QMouseEvent) -> None:
        super().mouse_press_event(event)
        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = QPointF(self.canvas.map_scene_to_image(event.position().toPoint()))

        if self._editing:
            handle = self._handle_at(pos)
            if handle >= 0:
                self._mode = self.MODE_RESIZE
                self._resize_handle = handle
                self._drag_offset = QPointF()
                return

            if self._rect.contains(pos):
                self._mode = self.MODE_MOVE
                self._drag_offset = QPointF(
                    pos.x() - self._rect.x(),
                    pos.y() - self._rect.y(),
                )
                return

            self.commit()
            return

        self._start_pos = QPointF(pos)
        self._mode = self.MODE_CREATE

    def mouse_move_event(self, event: QMouseEvent) -> None:
        super().mouse_move_event(event)
        pos = QPointF(self.canvas.map_scene_to_image(event.position().toPoint()))

        if self._mode == self.MODE_CREATE and self._start_pos:
            self._rect = QRectF(self._start_pos, pos).normalized()
            self.canvas.update_preview()
            return

        if self._mode == self.MODE_RESIZE and self._resize_handle >= 0:
            if self._drag_offset.isNull():
                self._drag_offset = pos
            else:
                d = pos - self._drag_offset
                self._rect = self._rect_from_handle(self._resize_handle, d)
                self._drag_offset = pos
                self.canvas.update_preview()
            return

        if self._mode == self.MODE_MOVE:
            r = QRectF(self._rect)
            r.moveTopLeft(
                QPointF(
                    pos.x() - self._drag_offset.x(),
                    pos.y() - self._drag_offset.y(),
                )
            )
            self._rect = r
            self.canvas.update_preview()
            return

        if self._editing:
            handle = self._handle_at(pos)
            if handle >= 0:
                self.canvas.setCursor(self._cursor_for_handle(handle))
            elif self._rect.contains(pos):
                self.canvas.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.canvas.setCursor(self.cursor())

    def mouse_release_event(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._mode == self.MODE_CREATE:
            self._mode = self.MODE_NONE
            if self._rect.width() > 5 and self._rect.height() > 5:
                self._editing = True
                self._text = ""
                self._cursor_pos = 0
                self.editing_started.emit()
            else:
                fm = QFontMetrics(self._make_font())
                w = max(fm.averageCharWidth() * 20, 100)
                h = max(fm.height() * 2, 40)
                if self._start_pos:
                    self._rect = QRectF(
                        self._start_pos.x(),
                        self._start_pos.y(),
                        w,
                        h,
                    )
                self._editing = True
                self._text = ""
                self._cursor_pos = 0
                self.editing_started.emit()
            self.canvas.update_preview()
            return

        if self._mode in (self.MODE_MOVE, self.MODE_RESIZE):
            self._mode = self.MODE_NONE
            self._resize_handle = -1
            self._drag_offset = QPointF()
            return

    def key_press_event(self, event: QKeyEvent) -> None:
        if not self._editing:
            if event.key() == Qt.Key.Key_Escape:
                self._cancel()
            return

        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self._text += "\n"
            self._cursor_pos = len(self._text)
        elif event.key() == Qt.Key.Key_Backspace:
            if self._cursor_pos > 0:
                self._text = self._text[: self._cursor_pos - 1] + self._text[self._cursor_pos :]
                self._cursor_pos -= 1
        elif event.key() == Qt.Key.Key_Delete:
            if self._cursor_pos < len(self._text):
                self._text = self._text[: self._cursor_pos] + self._text[self._cursor_pos + 1 :]
        elif event.key() == Qt.Key.Key_Left:
            self._cursor_pos = max(0, self._cursor_pos - 1)
        elif event.key() == Qt.Key.Key_Right:
            self._cursor_pos = min(len(self._text), self._cursor_pos + 1)
        elif event.key() == Qt.Key.Key_Escape:
            self._cancel()
            return
        elif event.key() == Qt.Key.Key_Home:
            self._cursor_pos = 0
        elif event.key() == Qt.Key.Key_End:
            self._cursor_pos = len(self._text)
        elif event.text() and event.text()[0].isprintable():
            self._text = (
                self._text[: self._cursor_pos] + event.text() + self._text[self._cursor_pos :]
            )
            self._cursor_pos += len(event.text())
        else:
            return

        self.canvas.update_preview()

    def paint_overlay(self, painter: QPainter) -> None:
        if self._mode == self.MODE_CREATE and self._rect.isValid():
            painter.setPen(QPen(QColor(0, 120, 255), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(0, 120, 255, 20)))
            painter.drawRect(self._rect)
            return

        if not self._editing or not self._rect.isValid():
            return

        r = self._rect

        painter.setPen(QPen(QColor(0, 120, 255), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(r)

        for pt, _ in self._get_handles():
            hr = QRectF(pt.x() - HANDLE_HALF, pt.y() - HANDLE_HALF, HANDLE_SIZE, HANDLE_SIZE)
            painter.fillRect(hr, QColor(255, 255, 255))
            painter.setPen(QPen(QColor(0, 120, 255), 1))
            painter.drawRect(hr)

        font = self._make_font()
        painter.setFont(font)
        painter.setPen(QPen(self._text_color))

        doc = QTextDocument(self._text)
        doc.setDefaultFont(font)
        doc.setTextWidth(max(r.width(), 1))

        painter.save()
        painter.translate(r.topLeft())
        clip = QRectF(0, 0, r.width(), r.height())
        painter.setClipRect(clip)
        doc.drawContents(painter)
        painter.restore()

        caret = self._caret_rect()
        if self._cursor_pos <= len(self._text):
            painter.setPen(QPen(self._text_color))
            painter.drawLine(
                QPointF(caret.x(), caret.y()),
                QPointF(caret.x(), caret.y() + caret.height()),
            )

    def deactivate(self) -> None:
        if self._editing:
            self.commit()
        super().deactivate()
