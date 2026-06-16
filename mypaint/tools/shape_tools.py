from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)

from .base_tool import BaseTool

FILL_OUTLINE = "outline"
FILL_FILL = "fill"
FILL_BOTH = "both"

STROKE_SOLID = Qt.PenStyle.SolidLine
STROKE_DASHED = Qt.PenStyle.DashLine
STROKE_DOTTED = Qt.PenStyle.DotLine

HANDLE_SIZE = 8
HANDLE_HALF = HANDLE_SIZE // 2


class ShapeTool(BaseTool):
    def __init__(self, canvas_widget, shape_name: str):
        super().__init__(canvas_widget)
        self._shape_name = shape_name
        self._size = 1
        self._fill_mode = FILL_OUTLINE
        self._stroke_style = STROKE_SOLID
        self._drawing = False
        self._start_point: QPoint | None = None
        self._current_point: QPoint | None = None
        self._shift_pressed = False
        self._pressed_button = Qt.MouseButton.NoButton

        self._committal = False
        self._committal_start: QPointF | None = None
        self._committal_end: QPointF | None = None
        self._committal_params: dict = {}
        self._resizing = False
        self._resize_handle = -1
        self._resize_start: QPointF | None = None
        self._moving = False
        self._move_start: QPointF | None = None
        self._move_origin_start: QPointF | None = None
        self._move_origin_end: QPointF | None = None

    def name(self) -> str:
        return self._shape_name.capitalize()

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    def set_size(self, size: int) -> None:
        self._size = max(1, size)

    def set_fill_mode(self, mode: str) -> None:
        self._fill_mode = mode

    def set_stroke_style(self, style: Qt.PenStyle) -> None:
        self._stroke_style = style

    def _enter_committal(self) -> None:
        self._committal = True
        self._committal_start = QPointF(self._start_point)
        self._committal_end = QPointF(self._current_point)
        self._committal_params = {
            "pressed_button": self._pressed_button,
        }

    def _exit_committal(self) -> None:
        self._committal = False
        self._committal_start = None
        self._committal_end = None
        self._committal_params.clear()
        self._resizing = False
        self._resize_handle = -1
        self._resize_start = None
        self._moving = False
        self._move_start = None
        self._move_origin_start = None
        self._move_origin_end = None

    def _get_committal_rect(self) -> QRectF:
        if self._committal_start is None or self._committal_end is None:
            return QRectF()
        return QRectF(self._committal_start, self._committal_end).normalized()

    def _commit_shape(self) -> None:
        if not self._committal:
            return
        old_start = self._start_point
        old_current = self._current_point
        old_button = self._pressed_button

        self._start_point = QPoint(self._committal_start.toPoint())
        self._current_point = QPoint(self._committal_end.toPoint())
        self._pressed_button = self._committal_params["pressed_button"]

        self._render_shape(final=True)
        self.canvas.commit_drawing()

        self._start_point = old_start
        self._current_point = old_current
        self._pressed_button = old_button

        self._exit_committal()

    def _cancel_shape(self) -> None:
        if not self._committal:
            return
        painter = QPainter(self.canvas.preview_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.canvas.preview_pixmap.rect(), Qt.GlobalColor.transparent)
        painter.end()
        self._exit_committal()
        self._start_point = None
        self._current_point = None
        self.canvas.update_preview()

    def _get_handle_at(self, pos: QPoint) -> int:
        r = self._get_committal_rect().toRect()
        if r.isNull() or r.isEmpty():
            return -1
        handles = [
            (0, r.topLeft()),
            (1, r.topRight()),
            (2, r.bottomRight()),
            (3, r.bottomLeft()),
            (4, QPoint(r.center().x(), r.top())),
            (5, QPoint(r.right(), r.center().y())),
            (6, QPoint(r.center().x(), r.bottom())),
            (7, QPoint(r.left(), r.center().y())),
        ]
        for idx, pt in handles:
            hr = QRect(pt.x() - HANDLE_HALF, pt.y() - HANDLE_HALF, HANDLE_SIZE, HANDLE_SIZE)
            if hr.contains(pos):
                return idx
        return -1

    def _resize_rect_from_handle(self, handle: int, delta: QPointF) -> QRectF:
        r = self._get_committal_rect()
        p1 = r.topLeft()
        p2 = r.bottomRight()
        if handle == 0:
            p1 += delta
        elif handle == 1:
            p1 += QPointF(0, delta.y())
            p2 += QPointF(delta.x(), 0)
        elif handle == 2:
            p2 += delta
        elif handle == 3:
            p1 += QPointF(delta.x(), 0)
            p2 += QPointF(0, delta.y())
        elif handle == 4:
            p1 += QPointF(0, delta.y())
        elif handle == 5:
            p2 += QPointF(delta.x(), 0)
        elif handle == 6:
            p2 += QPointF(0, delta.y())
        elif handle == 7:
            p1 += QPointF(delta.x(), 0)
        return QRectF(p1, p2).normalized()

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

    def mouse_press_event(self, event: QMouseEvent) -> None:
        super().mouse_press_event(event)
        pos = self.canvas.map_scene_to_image(event.position().toPoint())

        if self._committal:
            if event.button() == Qt.MouseButton.RightButton:
                self._commit_shape()
                return
            if event.button() == Qt.MouseButton.LeftButton:
                handle = self._get_handle_at(pos)
                if handle >= 0:
                    self._resizing = True
                    self._resize_handle = handle
                    self._resize_start = QPointF(pos)
                    return
                rect = self._get_committal_rect()
                if rect.contains(QPointF(pos)):
                    self._moving = True
                    self._move_start = QPointF(pos)
                    self._move_origin_start = QPointF(self._committal_start)
                    self._move_origin_end = QPointF(self._committal_end)
                    return
                self._commit_shape()
                self._drawing = True
                self._start_point = pos
                self._current_point = pos
                self._pressed_button = event.button()
                return
            return

        if event.button() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            return
        self._pressed_button = event.button()
        self._drawing = True
        self._start_point = self.canvas.map_scene_to_image(event.position().toPoint())
        self._current_point = self._start_point

    def mouse_move_event(self, event: QMouseEvent) -> None:
        super().mouse_move_event(event)
        pos = self.canvas.map_scene_to_image(event.position().toPoint())

        if self._resizing and self._resize_start:
            delta = QPointF(pos) - self._resize_start
            new_rect = self._resize_rect_from_handle(self._resize_handle, delta)
            self._committal_start = new_rect.topLeft()
            self._committal_end = new_rect.bottomRight()
            self._resize_start = QPointF(pos)
            self.canvas.update_preview()
            return

        if self._moving and self._move_start:
            delta = QPointF(pos) - self._move_start
            self._committal_start = self._move_origin_start + delta
            self._committal_end = self._move_origin_end + delta
            self.canvas.update_preview()
            return

        if self._committal:
            handle = self._get_handle_at(pos)
            if handle >= 0:
                self.canvas.setCursor(self._cursor_for_handle(handle))
            elif self._get_committal_rect().contains(QPointF(pos)):
                self.canvas.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
            else:
                self.canvas.setCursor(self.cursor())
            return

        if not self._drawing:
            return
        self._current_point = pos
        self.canvas.update_preview()

    def mouse_release_event(self, event: QMouseEvent) -> None:
        if self._resizing:
            self._resizing = False
            self._resize_handle = -1
            self._resize_start = None
            super().mouse_release_event(event)
            return
        if self._moving:
            self._moving = False
            self._move_start = None
            self._move_origin_start = None
            self._move_origin_end = None
            super().mouse_release_event(event)
            return
        if self._drawing:
            self._drawing = False
            self._enter_committal()
            self._start_point = None
            self._current_point = None
            self.canvas.update_preview()
            return
        super().mouse_release_event(event)

    def key_press_event(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and self._committal:
            self._cancel_shape()
            event.accept()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self._committal:
            self._commit_shape()
            event.accept()
        elif event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down) and self._committal:
            dx = (1 if event.key() == Qt.Key.Key_Right else -1) if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right) else 0
            dy = (1 if event.key() == Qt.Key.Key_Down else -1) if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down) else 0
            self._committal_start += QPointF(dx, dy)
            self._committal_end += QPointF(dx, dy)
            self.canvas.update_preview()
            event.accept()
        elif event.key() == Qt.Key.Key_Shift:
            self._shift_pressed = True
            if self._drawing:
                self.canvas.update_preview()

    def key_release_event(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Shift:
            self._shift_pressed = False
            if self._drawing:
                self.canvas.update_preview()

    def paint_overlay(self, painter: QPainter) -> None:
        if self._drawing and self._start_point is not None and self._current_point is not None:
            self._render_shape(final=False, painter=painter)
        elif self._committal:
            self._paint_committal_overlay(painter)

    def _paint_committal_overlay(self, painter: QPainter) -> None:
        if self._committal_start is None or self._committal_end is None:
            return
        rect = self._get_committal_rect()
        if rect.isNull() or rect.isEmpty():
            return

        old_start = self._start_point
        old_current = self._current_point
        self._start_point = QPoint(self._committal_start.toPoint())
        self._current_point = QPoint(self._committal_end.toPoint())
        self._render_shape(final=False, painter=painter)
        self._start_point = old_start
        self._current_point = old_current

        painter.setPen(QPen(QColor(0, 120, 255), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 120, 255)))
        rect_r = rect.toRect()
        pts = [
            rect_r.topLeft(),
            rect_r.topRight(),
            rect_r.bottomRight(),
            rect_r.bottomLeft(),
            QPoint(rect_r.center().x(), rect_r.top()),
            QPoint(rect_r.right(), rect_r.center().y()),
            QPoint(rect_r.center().x(), rect_r.bottom()),
            QPoint(rect_r.left(), rect_r.center().y()),
        ]
        for pt in pts:
            hr = QRectF(pt.x() - HANDLE_HALF, pt.y() - HANDLE_HALF, HANDLE_SIZE, HANDLE_SIZE)
            painter.drawRect(hr)

    def deactivate(self) -> None:
        if self._committal:
            self._commit_shape()
        super().deactivate()

    def _get_rect(self) -> QRectF:
        if self._start_point is None or self._current_point is None:
            return QRectF()
        p1 = QPointF(self._start_point)
        p2 = QPointF(self._current_point)
        if self._shift_pressed:
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            side = max(abs(dx), abs(dy))
            p2 = QPointF(
                p1.x() + side * (1 if dx >= 0 else -1), p1.y() + side * (1 if dy >= 0 else -1)
            )
        return QRectF(p1, p2).normalized()

    def _get_color1(self) -> QColor:
        if self._pressed_button == Qt.MouseButton.RightButton:
            return QColor(self.canvas.color2)
        return QColor(self.canvas.color1)

    def _get_color2(self) -> QColor:
        if self._pressed_button == Qt.MouseButton.RightButton:
            return QColor(self.canvas.color1)
        return QColor(self.canvas.color2)

    def _make_pen(self) -> QPen:
        c = self._get_color1()
        pen = QPen(
            c, self._size, self._stroke_style, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin
        )
        return pen

    def _make_fill_brush(self) -> QBrush:
        return QBrush(self._get_color2())

    def _render_shape(self, final: bool, painter: QPainter | None = None) -> None:
        if self._start_point is None or self._current_point is None:
            return

        target_painter = painter
        own_painter = None
        if not final and painter is None:
            return
        if final:
            own_painter = QPainter(self.canvas.preview_pixmap)
            target_painter = own_painter

        if target_painter is None:
            return

        target_painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        fill_brush = (
            self._make_fill_brush()
            if self._fill_mode in (FILL_FILL, FILL_BOTH)
            else Qt.BrushStyle.NoBrush
        )
        outline_pen = (
            self._make_pen() if self._fill_mode in (FILL_OUTLINE, FILL_BOTH) else Qt.PenStyle.NoPen
        )

        if self._shape_name == "line":
            target_painter.setPen(self._make_pen())
            target_painter.drawLine(QPointF(self._start_point), QPointF(self._current_point))

        elif self._shape_name == "rectangle":
            rect = self._get_rect()
            if self._fill_mode in (FILL_FILL, FILL_BOTH):
                target_painter.fillRect(rect, fill_brush)
            if self._fill_mode in (FILL_OUTLINE, FILL_BOTH):
                target_painter.setPen(outline_pen)
                target_painter.drawRect(rect)

        elif self._shape_name == "ellipse":
            rect = self._get_rect()
            if self._fill_mode in (FILL_FILL, FILL_BOTH):
                target_painter.setBrush(fill_brush)
                target_painter.setPen(Qt.PenStyle.NoPen)
                target_painter.drawEllipse(rect)
            if self._fill_mode in (FILL_OUTLINE, FILL_BOTH):
                target_painter.setBrush(Qt.BrushStyle.NoBrush)
                target_painter.setPen(outline_pen)
                target_painter.drawEllipse(rect)

        elif self._shape_name == "rounded_rect":
            rect = self._get_rect()
            radius = min(rect.width(), rect.height()) * 0.2
            if self._fill_mode in (FILL_FILL, FILL_BOTH):
                target_painter.setBrush(fill_brush)
                target_painter.setPen(Qt.PenStyle.NoPen)
                target_painter.drawRoundedRect(rect, radius, radius)
            if self._fill_mode in (FILL_OUTLINE, FILL_BOTH):
                target_painter.setBrush(Qt.BrushStyle.NoBrush)
                target_painter.setPen(outline_pen)
                target_painter.drawRoundedRect(rect, radius, radius)

        elif self._shape_name == "arrow_right":
            rect = self._get_rect()
            if rect.width() < 4 or rect.height() < 4:
                return
            cy = rect.center().y()
            left = rect.left()
            right = rect.right()
            body_right = right - rect.height() * 0.4
            body_half = rect.height() * 0.15
            if self._fill_mode in (FILL_FILL, FILL_BOTH):
                path = QPainterPath()
                path.moveTo(left, cy - body_half)
                path.lineTo(body_right, cy - body_half)
                path.lineTo(body_right, rect.top())
                path.lineTo(right, cy)
                path.lineTo(body_right, rect.bottom())
                path.lineTo(body_right, cy + body_half)
                path.lineTo(left, cy + body_half)
                path.closeSubpath()
                target_painter.setBrush(fill_brush)
                target_painter.setPen(Qt.PenStyle.NoPen)
                target_painter.drawPath(path)
            if self._fill_mode in (FILL_OUTLINE, FILL_BOTH):
                target_painter.setBrush(Qt.BrushStyle.NoBrush)
                target_painter.setPen(outline_pen)
                path = QPainterPath()
                path.moveTo(left, cy - body_half)
                path.lineTo(body_right, cy - body_half)
                path.lineTo(body_right, rect.top())
                path.lineTo(right, cy)
                path.lineTo(body_right, rect.bottom())
                path.lineTo(body_right, cy + body_half)
                path.lineTo(left, cy + body_half)
                path.closeSubpath()
                target_painter.drawPath(path)

        elif self._shape_name == "arrow_left":
            rect = self._get_rect()
            if rect.width() < 4 or rect.height() < 4:
                return
            cy = rect.center().y()
            left = rect.left()
            right = rect.right()
            body_left = left + rect.height() * 0.4
            body_half = rect.height() * 0.15
            if self._fill_mode in (FILL_FILL, FILL_BOTH):
                path = QPainterPath()
                path.moveTo(right, cy - body_half)
                path.lineTo(body_left, cy - body_half)
                path.lineTo(body_left, rect.top())
                path.lineTo(left, cy)
                path.lineTo(body_left, rect.bottom())
                path.lineTo(body_left, cy + body_half)
                path.lineTo(right, cy + body_half)
                path.closeSubpath()
                target_painter.setBrush(fill_brush)
                target_painter.setPen(Qt.PenStyle.NoPen)
                target_painter.drawPath(path)
            if self._fill_mode in (FILL_OUTLINE, FILL_BOTH):
                target_painter.setBrush(Qt.BrushStyle.NoBrush)
                target_painter.setPen(outline_pen)
                path = QPainterPath()
                path.moveTo(right, cy - body_half)
                path.lineTo(body_left, cy - body_half)
                path.lineTo(body_left, rect.top())
                path.lineTo(left, cy)
                path.lineTo(body_left, rect.bottom())
                path.lineTo(body_left, cy + body_half)
                path.lineTo(right, cy + body_half)
                path.closeSubpath()
                target_painter.drawPath(path)

        elif self._shape_name == "arrow_up":
            rect = self._get_rect()
            if rect.width() < 4 or rect.height() < 4:
                return
            cx = rect.center().x()
            top = rect.top()
            bottom = rect.bottom()
            body_top = top + rect.width() * 0.4
            body_half = rect.width() * 0.15
            if self._fill_mode in (FILL_FILL, FILL_BOTH):
                path = QPainterPath()
                path.moveTo(cx - body_half, bottom)
                path.lineTo(cx - body_half, body_top)
                path.lineTo(rect.left(), body_top)
                path.lineTo(cx, top)
                path.lineTo(rect.right(), body_top)
                path.lineTo(cx + body_half, body_top)
                path.lineTo(cx + body_half, bottom)
                path.closeSubpath()
                target_painter.setBrush(fill_brush)
                target_painter.setPen(Qt.PenStyle.NoPen)
                target_painter.drawPath(path)
            if self._fill_mode in (FILL_OUTLINE, FILL_BOTH):
                target_painter.setBrush(Qt.BrushStyle.NoBrush)
                target_painter.setPen(outline_pen)
                path = QPainterPath()
                path.moveTo(cx - body_half, bottom)
                path.lineTo(cx - body_half, body_top)
                path.lineTo(rect.left(), body_top)
                path.lineTo(cx, top)
                path.lineTo(rect.right(), body_top)
                path.lineTo(cx + body_half, body_top)
                path.lineTo(cx + body_half, bottom)
                path.closeSubpath()
                target_painter.drawPath(path)

        elif self._shape_name == "arrow_down":
            rect = self._get_rect()
            if rect.width() < 4 or rect.height() < 4:
                return
            cx = rect.center().x()
            top = rect.top()
            bottom = rect.bottom()
            body_bottom = bottom - rect.width() * 0.4
            body_half = rect.width() * 0.15
            if self._fill_mode in (FILL_FILL, FILL_BOTH):
                path = QPainterPath()
                path.moveTo(cx - body_half, top)
                path.lineTo(cx - body_half, body_bottom)
                path.lineTo(rect.left(), body_bottom)
                path.lineTo(cx, bottom)
                path.lineTo(rect.right(), body_bottom)
                path.lineTo(cx + body_half, body_bottom)
                path.lineTo(cx + body_half, top)
                path.closeSubpath()
                target_painter.setBrush(fill_brush)
                target_painter.setPen(Qt.PenStyle.NoPen)
                target_painter.drawPath(path)
            if self._fill_mode in (FILL_OUTLINE, FILL_BOTH):
                target_painter.setBrush(Qt.BrushStyle.NoBrush)
                target_painter.setPen(outline_pen)
                path = QPainterPath()
                path.moveTo(cx - body_half, top)
                path.lineTo(cx - body_half, body_bottom)
                path.lineTo(rect.left(), body_bottom)
                path.lineTo(cx, bottom)
                path.lineTo(rect.right(), body_bottom)
                path.lineTo(cx + body_half, body_bottom)
                path.lineTo(cx + body_half, top)
                path.closeSubpath()
                target_painter.drawPath(path)

        if own_painter:
            own_painter.end()
            if final:
                self.canvas.update_preview()


class LineTool(ShapeTool):
    def __init__(self, canvas_widget):
        super().__init__(canvas_widget, "line")


class RectangleTool(ShapeTool):
    def __init__(self, canvas_widget):
        super().__init__(canvas_widget, "rectangle")


class EllipseTool(ShapeTool):
    def __init__(self, canvas_widget):
        super().__init__(canvas_widget, "ellipse")


class RoundedRectTool(ShapeTool):
    def __init__(self, canvas_widget):
        super().__init__(canvas_widget, "rounded_rect")


class CurveTool(BaseTool):
    STATE_LINE = 0   # drawing initial straight line
    STATE_BEND1 = 1  # waiting for first bend click
    STATE_BEND2 = 2  # waiting for second bend click (finalizes)

    MIN_DRAG_DIST = 3  # minimum pixels to count as a real line

    def __init__(self, canvas_widget):
        super().__init__(canvas_widget)
        self._size = 1
        self._stroke_style = STROKE_SOLID
        self._state = self.STATE_LINE
        self._start_point: QPointF | None = None
        self._end_point: QPointF | None = None
        self._curve_point1: QPointF | None = None
        self._curve_point2: QPointF | None = None
        self._drawing = False

    def name(self) -> str:
        return "Curve"

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    def set_size(self, size: int) -> None:
        self._size = max(1, size)

    def set_stroke_style(self, style: Qt.PenStyle) -> None:
        self._stroke_style = style

    def _make_pen(self) -> QPen:
        return QPen(
            QColor(self.canvas.color1),
            self._size,
            self._stroke_style,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )

    def _reset(self) -> None:
        self._state = self.STATE_LINE
        self._drawing = False
        self._start_point = None
        self._end_point = None
        self._curve_point1 = None
        self._curve_point2 = None
        self.canvas.update_preview()

    def mouse_press_event(self, event: QMouseEvent) -> None:
        super().mouse_press_event(event)
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = QPointF(self.canvas.map_scene_to_image(event.position().toPoint()))

        if self._state == self.STATE_LINE:
            self._start_point = pos
            self._end_point = pos
            self._drawing = True
        elif self._state == self.STATE_BEND1:
            self._curve_point1 = pos
            self._state = self.STATE_BEND2
            self.canvas.update_preview()
        elif self._state == self.STATE_BEND2:
            self._curve_point2 = pos
            self._finalize_curve()
            self._reset()

    def mouse_move_event(self, event: QMouseEvent) -> None:
        super().mouse_move_event(event)
        pos = QPointF(self.canvas.map_scene_to_image(event.position().toPoint()))

        if self._state == self.STATE_LINE and self._drawing:
            self._end_point = pos
            self.canvas.update_preview()
        elif self._state == self.STATE_BEND1:
            self._curve_point1 = pos
            self.canvas.update_preview()
        elif self._state == self.STATE_BEND2:
            self._curve_point2 = pos
            self.canvas.update_preview()

    def mouse_release_event(self, event: QMouseEvent) -> None:
        if self._state == self.STATE_LINE and self._drawing:
            self._drawing = False
            dx = abs(self._end_point.x() - self._start_point.x())
            dy = abs(self._end_point.y() - self._start_point.y())
            if dx < self.MIN_DRAG_DIST and dy < self.MIN_DRAG_DIST:
                self._reset()
                return
            self._state = self.STATE_BEND1
            self.canvas.update_preview()
        super().mouse_release_event(event)

    def mouse_double_click_event(self, event: QMouseEvent) -> None:
        if self._state == self.STATE_BEND1 and self._start_point and self._end_point:
            self._curve_point1 = QPointF(self.canvas.map_scene_to_image(event.position().toPoint()))
            self._curve_point2 = self._curve_point1
            self._finalize_curve()
            self._reset()

    def _finalize_curve(self) -> None:
        if self._start_point is None or self._end_point is None or self._curve_point1 is None:
            self._reset()
            return
        p0 = self._start_point
        p3 = self._end_point
        p1 = self._curve_point1
        p2 = self._curve_point2 or p1

        path = QPainterPath()
        path.moveTo(p0)
        path.cubicTo(p1, p2, p3)

        painter = QPainter(self.canvas.preview_pixmap)
        painter.setPen(self._make_pen())
        painter.drawPath(path)
        painter.end()
        self.canvas.commit_drawing()

    def key_press_event(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._reset()

    def paint_overlay(self, painter: QPainter) -> None:

        if self._state == self.STATE_LINE and self._drawing and self._start_point and self._end_point:
            if self._start_point != self._end_point:
                painter.setPen(QPen(QColor(100, 100, 255), 1, Qt.PenStyle.DashLine))
                painter.drawLine(QPointF(self._start_point), QPointF(self._end_point))
            return

        if self._state == self.STATE_BEND1 and self._start_point and self._end_point:
            cp = self._curve_point1 or self._end_point
            pen = QPen(QColor(100, 100, 255), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(self._start_point, cp)
            painter.drawLine(self._end_point, cp)
            painter.drawEllipse(cp, 3, 3)
            return

        if self._state == self.STATE_BEND2 and self._start_point and self._end_point:
            cp1 = self._curve_point1 or self._end_point
            cp2 = self._curve_point2 or cp1
            path = QPainterPath()
            path.moveTo(self._start_point)
            path.cubicTo(cp1, cp2, self._end_point)
            painter.setPen(QPen(QColor(100, 100, 255), 2, Qt.PenStyle.SolidLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
            painter.drawEllipse(cp1, 3, 3)
            painter.drawEllipse(cp2, 3, 3)


class PolygonTool(BaseTool):
    CLOSE_DIST = 10  # image-pixel proximity to close polygon

    def __init__(self, canvas_widget):
        super().__init__(canvas_widget)
        self._size = 1
        self._fill_mode = FILL_OUTLINE
        self._stroke_style = STROKE_SOLID
        self._vertices: list[QPointF] = []
        self._building = False
        self._current_pos: QPointF | None = None
        self._near_start = False

    def name(self) -> str:
        return "Polygon"

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    def set_size(self, size: int) -> None:
        self._size = max(1, size)

    def set_fill_mode(self, mode: str) -> None:
        self._fill_mode = mode

    def set_stroke_style(self, style: Qt.PenStyle) -> None:
        self._stroke_style = style

    def _make_pen(self) -> QPen:
        return QPen(
            QColor(self.canvas.color1),
            self._size,
            self._stroke_style,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )

    def _make_fill_brush(self) -> QBrush:
        return QBrush(QColor(self.canvas.color2))

    def _finalize_polygon(self) -> None:
        if len(self._vertices) < 3:
            self._building = False
            self._vertices.clear()
            self._current_pos = None
            self._near_start = False
            self.canvas.update_preview()
            return
        self._building = False
        self._render_polygon(final=True)
        self.canvas.commit_drawing()
        self._vertices.clear()
        self._current_pos = None
        self._near_start = False
        self.canvas.update_preview()

    def _near_first_vertex(self, pos: QPointF) -> bool:
        if not self._vertices:
            return False
        first = self._vertices[0]
        dx = pos.x() - first.x()
        dy = pos.y() - first.y()
        return (dx * dx + dy * dy) <= self.CLOSE_DIST * self.CLOSE_DIST

    def mouse_press_event(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton and self._building:
            self._finalize_polygon()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = QPointF(self.canvas.map_scene_to_image(event.position().toPoint()))

        if not self._building:
            self._building = True
            self._vertices = [pos]
            self._near_start = False
        elif self._near_start and len(self._vertices) >= 3:
            self._vertices.append(self._vertices[0])
            self._finalize_polygon()
        else:
            self._vertices.append(pos)

        self.canvas.update_preview()

    def mouse_move_event(self, event: QMouseEvent) -> None:
        super().mouse_move_event(event)
        pos = QPointF(self.canvas.map_scene_to_image(event.position().toPoint()))
        self._current_pos = pos
        if self._building:
            self._near_start = self._near_first_vertex(pos)
            self.canvas.update_preview()

    def mouse_double_click_event(self, event: QMouseEvent) -> None:
        if self._building:
            pos = QPointF(self.canvas.map_scene_to_image(event.position().toPoint()))
            if event.button() == Qt.MouseButton.LeftButton:
                self._vertices.append(pos)
            self._finalize_polygon()

    def mouse_release_event(self, event: QMouseEvent) -> None:
        super().mouse_release_event(event)

    def paint_overlay(self, painter: QPainter) -> None:
        if not self._building or not self._vertices:
            return

        pts = list(self._vertices)
        if self._current_pos:
            pts.append(self._current_pos)

        preview_pen = QPen(QColor(100, 100, 255), 1, Qt.PenStyle.DashLine)
        if self._near_start and len(self._vertices) >= 3:
            preview_pen = QPen(QColor(0, 200, 0), 2, Qt.PenStyle.SolidLine)
        painter.setPen(preview_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if len(pts) >= 2:
            polygon = QPolygonF(pts)
            painter.drawPolyline(polygon)

        for v in self._vertices:
            painter.drawEllipse(v, 2, 2)

        if self._near_start and self._vertices:
            first = self._vertices[0]
            painter.setPen(QPen(QColor(0, 200, 0), 2, Qt.PenStyle.SolidLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(first, 4, 4)

    def _render_polygon(self, final: bool = False) -> None:
        if len(self._vertices) < 2:
            return

        painter = QPainter(self.canvas.preview_pixmap)

        polygon = QPolygonF(self._vertices)

        if self._fill_mode in (FILL_FILL, FILL_BOTH):
            painter.setBrush(self._make_fill_brush())
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(polygon)

        if self._fill_mode in (FILL_OUTLINE, FILL_BOTH):
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(self._make_pen())
            painter.drawPolygon(polygon)

        painter.end()

    def key_press_event(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._building = False
            self._vertices.clear()
            self._current_pos = None
            self._near_start = False
            self.canvas.update_preview()


class ArrowRightTool(ShapeTool):
    def __init__(self, canvas_widget):
        super().__init__(canvas_widget, "arrow_right")


class ArrowLeftTool(ShapeTool):
    def __init__(self, canvas_widget):
        super().__init__(canvas_widget, "arrow_left")


class ArrowUpTool(ShapeTool):
    def __init__(self, canvas_widget):
        super().__init__(canvas_widget, "arrow_up")


class ArrowDownTool(ShapeTool):
    def __init__(self, canvas_widget):
        super().__init__(canvas_widget, "arrow_down")
