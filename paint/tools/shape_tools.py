from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
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

    def mouse_press_event(self, event: QMouseEvent) -> None:
        super().mouse_press_event(event)
        if event.button() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            return
        self._drawing = True
        self._start_point = self.canvas.map_scene_to_image(event.position().toPoint())
        self._current_point = self._start_point

    def mouse_move_event(self, event: QMouseEvent) -> None:
        super().mouse_move_event(event)
        if not self._drawing:
            return
        self._current_point = self.canvas.map_scene_to_image(event.position().toPoint())
        self.canvas.update_preview()

    def mouse_release_event(self, event: QMouseEvent) -> None:
        if self._drawing:
            self._drawing = False
            self._render_shape(final=True)
            self._start_point = None
            self._current_point = None
            self.canvas.commit_drawing()
        super().mouse_release_event(event)

    def key_press_event(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Shift:
            self._shift_pressed = True
            if self._drawing:
                self.canvas.update_preview()

    def key_release_event(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Shift:
            self._shift_pressed = False
            if self._drawing:
                self.canvas.update_preview()

    def paint_overlay(self, painter: QPainter) -> None:
        if not self._drawing or self._start_point is None or self._current_point is None:
            return
        self._render_shape(final=False, painter=painter)

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
        return QColor(self.canvas.color1)

    def _get_color2(self) -> QColor:
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
    STATE_LINE = 0
    STATE_BEND1 = 1
    STATE_BEND2 = 2

    def __init__(self, canvas_widget):
        super().__init__(canvas_widget)
        self._size = 1
        self._state = self.STATE_LINE
        self._points: list[QPointF] = []
        self._curve_point1: QPointF | None = None
        self._curve_point2: QPointF | None = None
        self._drawing = False

    def name(self) -> str:
        return "Curve"

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    def set_size(self, size: int) -> None:
        self._size = max(1, size)

    def _make_pen(self) -> QPen:
        return QPen(
            QColor(self.canvas.color1),
            self._size,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )

    def mouse_press_event(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = QPointF(self.canvas.map_scene_to_image(event.position().toPoint()))

        if self._state == self.STATE_LINE:
            self._points = [pos]
            self._drawing = True
            self._state = self.STATE_BEND1
        elif self._state == self.STATE_BEND1:
            self._curve_point1 = pos
            self._state = self.STATE_BEND2
            self.canvas.update_preview()
        elif self._state == self.STATE_BEND2:
            self._curve_point2 = pos
            self._finalize_curve()
            self._state = self.STATE_LINE
            self._drawing = False
            self.canvas.commit_drawing()

    def mouse_move_event(self, event: QMouseEvent) -> None:
        super().mouse_move_event(event)
        pos = QPointF(self.canvas.map_scene_to_image(event.position().toPoint()))

        if self._state == self.STATE_LINE and self._drawing and len(self._points) >= 1:
            self._points = [self._points[0], pos]
            self.canvas.update_preview()
        elif self._state == self.STATE_BEND1:
            self._curve_point1 = pos
            self.canvas.update_preview()
        elif self._state == self.STATE_BEND2:
            self._curve_point2 = pos
            self.canvas.update_preview()

    def _finalize_curve(self) -> None:
        if len(self._points) < 2 or self._curve_point1 is None:
            return
        p0 = self._points[0]
        p3 = self._points[-1] if len(self._points) > 1 else p0
        p1 = self._curve_point1
        p2 = self._curve_point2 or p1

        path = QPainterPath()
        path.moveTo(p0)
        path.cubicTo(p1, p2, p3)

        painter = QPainter(self.canvas.preview_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(self._make_pen())
        painter.drawPath(path)
        painter.end()
        self.canvas.update_preview()

    def mouse_release_event(self, event: QMouseEvent) -> None:
        pass

    def key_press_event(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._state = self.STATE_LINE
            self._drawing = False
            self._points.clear()
            self._curve_point1 = None
            self._curve_point2 = None
            self.canvas.update_preview()

    def paint_overlay(self, painter: QPainter) -> None:
        if not self._drawing or not self._points:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor(100, 100, 255), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self._state == self.STATE_LINE and len(self._points) == 2:
            painter.drawLine(self._points[0], self._points[1])

        if self._state == self.STATE_BEND1 and self._curve_point1:
            p0 = self._points[0]
            p3 = self._points[1] if len(self._points) > 1 else p0
            painter.drawLine(p0, self._curve_point1)
            painter.drawLine(p3, self._curve_point1)
            painter.drawEllipse(self._curve_point1, 3, 3)

        if self._state == self.STATE_BEND2 and self._curve_point1 and self._curve_point2:
            p0 = self._points[0]
            p3 = self._points[1] if len(self._points) > 1 else p0
            path = QPainterPath()
            path.moveTo(p0)
            path.cubicTo(self._curve_point1, self._curve_point2, p3)
            painter.setPen(QPen(QColor(100, 100, 255), 2, Qt.PenStyle.SolidLine))
            painter.drawPath(path)
            painter.drawEllipse(self._curve_point1, 3, 3)
            painter.drawEllipse(self._curve_point2, 3, 3)


class PolygonTool(BaseTool):
    def __init__(self, canvas_widget):
        super().__init__(canvas_widget)
        self._size = 1
        self._fill_mode = FILL_OUTLINE
        self._stroke_style = STROKE_SOLID
        self._vertices: list[QPointF] = []
        self._building = False
        self._current_pos: QPointF | None = None

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

    def mouse_press_event(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = QPointF(self.canvas.map_scene_to_image(event.position().toPoint()))

        if not self._building:
            self._building = True
            self._vertices = [pos]
        else:
            self._vertices.append(pos)
            self._render_polygon()

        self.canvas.update_preview()

    def mouse_move_event(self, event: QMouseEvent) -> None:
        super().mouse_move_event(event)
        pos = QPointF(self.canvas.map_scene_to_image(event.position().toPoint()))
        self._current_pos = pos
        if self._building:
            self.canvas.update_preview()

    def mouse_double_click_event(self, event: QMouseEvent) -> None:
        if self._building and len(self._vertices) >= 3:
            self._building = False
            self._render_polygon(final=True)
            self.canvas.commit_drawing()
            self._vertices.clear()
            self._current_pos = None
            self.canvas.update_preview()

    def mouse_release_event(self, event: QMouseEvent) -> None:
        pass

    def paint_overlay(self, painter: QPainter) -> None:
        if not self._building or not self._vertices:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor(100, 100, 255), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        polygon = QPolygonF(self._vertices)
        if self._current_pos:
            pts = list(self._vertices) + [self._current_pos]
            polygon2 = QPolygonF(pts)
            painter.drawPolyline(polygon2)
        else:
            painter.drawPolygon(polygon)

        for v in self._vertices:
            painter.drawEllipse(v, 2, 2)

    def _render_polygon(self, final: bool = False) -> None:
        if len(self._vertices) < 2:
            return

        painter = QPainter(self.canvas.preview_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

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
            self.canvas.update_preview()
