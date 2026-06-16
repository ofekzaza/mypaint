from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QTransform,
)

from .base_tool import BaseTool

HANDLE_SIZE = 8
HANDLE_HALF = HANDLE_SIZE // 2


class SelectionTool(BaseTool):
    MODE_RECT = "rect"
    MODE_FREEFORM = "freeform"

    def __init__(self, canvas_widget, mode: str = MODE_RECT):
        super().__init__(canvas_widget)
        self._mode = mode
        self._selecting = False
        self._has_selection = False
        self._moving = False
        self._resizing = False
        self._resize_handle = -1
        self._rotating = False
        self._rotation_angle = 0.0

        self._start_point: QPoint | None = None
        self._current_point: QPoint | None = None
        self._selection_rect = QRect()
        self._freeform_path: list[QPoint] = []

        self._selection_content: QImage | None = None
        self._selection_offset = QPoint(0, 0)
        self._drag_start = QPoint(0, 0)

        self._transparent_select = False

        self._move_origin_rect: QRect | None = None
        self._selection_from_canvas = False

    def name(self) -> str:
        return f"Selection ({self._mode})"

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    def set_transparent(self, enabled: bool) -> None:
        self._transparent_select = enabled

    def reset_selection(self) -> None:
        self._has_selection = False
        self._selection_rect = QRect()
        self._selection_content = None
        self._freeform_path.clear()
        self._rotation_angle = 0.0
        self._moving = False
        self._resizing = False
        self.canvas.clear_selection_overlay()
        self.canvas.update_preview()

    def select_all(self) -> None:
        if self._has_selection:
            self.commit_selection()
        img = self.canvas.image()
        self._selection_rect = QRect(0, 0, img.width(), img.height())
        self._selection_content = img.copy(self._selection_rect)
        self._has_selection = True
        self._selection_from_canvas = True
        self._move_origin_rect = QRect(self._selection_rect)
        self._rotation_angle = 0.0
        self.canvas.update_preview()

    def invert_selection(self) -> None:
        if self._has_selection:
            self.commit_selection()
        img = self.canvas.image()
        full_rect = QRect(0, 0, img.width(), img.height())
        self._selection_rect = full_rect
        self._selection_content = img.copy(self._selection_rect)
        self._selection_from_canvas = True
        self._move_origin_rect = QRect(self._selection_rect)
        self.canvas.update_preview()

    def cut_selection(self) -> QImage | None:
        if not self._has_selection or self._selection_content is None:
            return None
        content = self._selection_content.copy()
        self._apply_to_canvas()
        self.reset_selection()
        return content

    def copy_selection(self) -> QImage | None:
        if not self._has_selection or self._selection_content is None:
            return None
        return self._selection_content.copy()

    def paste_selection(self, image: QImage, pos: QPoint | None = None) -> None:
        # Commit any existing floating selection first
        if self._has_selection:
            self.commit_selection()

        self._selection_content = image.copy()
        w, h = image.width(), image.height()
        img_w = self.canvas.image().width()
        img_h = self.canvas.image().height()
        if pos:
            x = max(0, min(pos.x(), img_w - w))
            y = max(0, min(pos.y(), img_h - h))
        else:
            x = max(0, (img_w - w) // 2)
            y = max(0, (img_h - h) // 2)
        self._selection_rect = QRect(x, y, w, h)
        self._has_selection = True
        self._rotation_angle = 0.0
        self._selection_from_canvas = False
        self._move_origin_rect = None
        self._moving = False
        self._resizing = False
        self.canvas.update_preview()

    def _get_rendered_content(self) -> QImage | None:
        if self._selection_content is None:
            return None
        if not self._transparent_select:
            return self._selection_content
        result = self._selection_content.convertToFormat(
            QImage.Format.Format_ARGB32_Premultiplied
        )
        key = QColor(Qt.GlobalColor.white)
        mask = result.createMaskFromColor(key.rgb(), Qt.MaskMode.MaskOutColor)
        result.setAlphaChannel(mask)
        return result

    def _apply_to_canvas(self) -> None:
        """Apply floating selection to canvas without destroying the selection state."""
        if self._selection_content is None or not self._has_selection:
            return

        img = self.canvas.image()
        self.canvas._undo.push_state(img.copy())

        painter = QPainter(img)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)

        if (
            self._selection_from_canvas
            and self._move_origin_rect is not None
            and self._move_origin_rect != self._selection_rect
        ):
            painter.fillRect(self._move_origin_rect, Qt.GlobalColor.white)

        if not self._transparent_select:
            painter.fillRect(self._selection_rect, Qt.GlobalColor.transparent)

        if self._rotation_angle != 0:
            transform = QTransform()
            center = self._selection_rect.center()
            transform.translate(center.x(), center.y())
            transform.rotate(self._rotation_angle)
            transform.translate(-center.x(), -center.y())
            painter.setTransform(transform)

        content = self._get_rendered_content()
        if content:
            if self._transparent_select:
                painter.setCompositionMode(
                    QPainter.CompositionMode.CompositionMode_SourceOver
                )
            painter.drawImage(self._selection_rect.topLeft(), content)
        painter.end()

        self.canvas.update_image_item()
        self.canvas._dirty = True
        self._selection_from_canvas = False
        self._move_origin_rect = None

    def commit_selection(self) -> None:
        self._apply_to_canvas()
        self.reset_selection()

    def _delete_selection(self) -> None:
        if not self._has_selection:
            return
        painter = QPainter(self.canvas.image())
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self._selection_rect, QColor(self.canvas.color2))
        painter.end()
        self.canvas.commit_drawing()

    def delete_selection(self) -> None:
        self._delete_selection()
        self.reset_selection()

    def _get_handle_at(self, pos: QPoint) -> int:
        if not self._has_selection:
            return -1
        r = self._selection_rect

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
            handle_rect = QRect(
                pt.x() - HANDLE_HALF, pt.y() - HANDLE_HALF, HANDLE_SIZE, HANDLE_SIZE
            )
            if handle_rect.contains(pos):
                return idx
        return -1

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

    def _resize_rect_from_handle(self, handle: int, delta: QPoint) -> QRect:
        r = QRect(self._selection_rect)
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

    def _scale_content_to_rect(self, new_rect: QRect) -> None:
        if self._selection_content is None or new_rect.isEmpty():
            return
        mode = Qt.TransformationMode.FastTransformation if self._transparent_select else Qt.TransformationMode.SmoothTransformation
        self._selection_content = self._selection_content.scaled(
            new_rect.size(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            mode,
        )

    def mouse_press_event(self, event: QMouseEvent) -> None:
        super().mouse_press_event(event)
        pos = self.canvas.map_scene_to_image(event.position().toPoint())

        if event.button() == Qt.MouseButton.RightButton and self._has_selection:
            self.commit_selection()
            return

        if event.button() == Qt.MouseButton.LeftButton and self._has_selection:
            handle = self._get_handle_at(pos)
            if handle >= 0:
                self._resizing = True
                self._resize_handle = handle
                self._start_point = pos
                return

            if self._selection_rect.contains(pos):
                self._moving = True
                self._drag_start = pos
                self._selection_offset = QPoint(
                    pos.x() - self._selection_rect.x(),
                    pos.y() - self._selection_rect.y(),
                )
                self._move_origin_rect = QRect(self._selection_rect)
                return

            self.commit_selection()

        if event.button() == Qt.MouseButton.LeftButton:
            self._selecting = True
            self._start_point = pos
            self._current_point = pos
            if self._mode == self.MODE_FREEFORM:
                self._freeform_path = [pos]

    def mouse_move_event(self, event: QMouseEvent) -> None:
        pos = self.canvas.map_scene_to_image(event.position().toPoint())

        if self._resizing and self._start_point:
            delta = pos - self._start_point
            new_rect = self._resize_rect_from_handle(self._resize_handle, delta)
            self._scale_content_to_rect(new_rect)
            self._selection_rect = new_rect
            self._start_point = pos
            self.canvas.update_preview()
            return

        if self._moving:
            dx = pos.x() - self._drag_start.x()
            dy = pos.y() - self._drag_start.y()
            self._selection_rect.moveTopLeft(
                QPoint(self._selection_rect.x() + dx, self._selection_rect.y() + dy)
            )
            self._drag_start = pos
            self.canvas.update_preview()
            return

        if self._selecting:
            self._current_point = pos
            if self._mode == self.MODE_FREEFORM:
                self._freeform_path.append(pos)
            self.canvas.update_preview()
            return

        if self._has_selection:
            handle = self._get_handle_at(pos)
            if handle >= 0:
                self.canvas.setCursor(self._cursor_for_handle(handle))
            elif self._selection_rect.contains(pos):
                self.canvas.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
            else:
                self.canvas.setCursor(self.cursor())

    def mouse_release_event(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._selecting:
            self._selecting = False
            if self._start_point and self._current_point:
                if self._mode == self.MODE_RECT:
                    self._selection_rect = QRect(
                        self._start_point, self._current_point
                    ).normalized()
                    if self._selection_rect.width() > 0 and self._selection_rect.height() > 0:
                        self._selection_content = self.canvas.image().copy(self._selection_rect)
                        self._has_selection = True
                        self._selection_from_canvas = True
                        self._move_origin_rect = QRect(self._selection_rect)
                    else:
                        self.reset_selection()
                elif len(self._freeform_path) >= 2:
                    poly = QPolygonF([QPointF(p) for p in self._freeform_path])
                    self._selection_rect = poly.boundingRect().toRect()
                    bounds = self.canvas.image().rect()
                    if not bounds.contains(self._selection_rect):
                        self._selection_rect = self._selection_rect.intersected(bounds)
                    if self._selection_rect.width() > 0 and self._selection_rect.height() > 0:
                        content = self.canvas.image().copy(self._selection_rect)
                        pts = []
                        ox, oy = self._selection_rect.x(), self._selection_rect.y()
                        for p in self._freeform_path:
                            pts.append(QPointF(p.x() - ox, p.y() - oy))
                        local_poly = QPolygonF(pts)
                        local_path = QPainterPath()
                        local_path.addPolygon(local_poly)
                        result = QImage(self._selection_rect.size(), QImage.Format.Format_ARGB32_Premultiplied)
                        result.fill(Qt.GlobalColor.transparent)
                        mp = QPainter(result)
                        mp.setRenderHint(QPainter.RenderHint.Antialiasing, False)
                        mp.setClipPath(local_path)
                        mp.drawImage(0, 0, content)
                        mp.end()
                        self._selection_content = result
                        self._has_selection = True
                        self._selection_from_canvas = True
                        self._move_origin_rect = QRect(self._selection_rect)
                    else:
                        self.reset_selection()
                else:
                    self.reset_selection()
            self._freeform_path.clear()
            self.canvas.update_preview()
            return

        if self._moving:
            self._moving = False
            return

        if self._resizing:
            self._resizing = False
            self._resize_handle = -1
            return

    def paint_overlay(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        if self._selecting and self._start_point and self._current_point:
            pen = QPen(QColor(0, 120, 255), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(0, 120, 255, 30)))
            if self._mode == self.MODE_RECT:
                rect = QRectF(self._start_point, self._current_point).normalized()
                painter.drawRect(rect)
            elif self._mode == self.MODE_FREEFORM:
                if len(self._freeform_path) >= 2:
                    pts = self._freeform_path + [self._current_point]
                    poly = QPolygonF([QPointF(p) for p in pts])
                    painter.drawPolygon(poly)

        if self._has_selection:
            img_rect = QRectF(self._selection_rect)

            # Draw origin ghost (for canvas selections during move)
            if (
                self._moving
                and self._selection_from_canvas
                and self._move_origin_rect is not None
                and self._move_origin_rect != self._selection_rect
            ):
                painter.fillRect(QRectF(self._move_origin_rect), Qt.GlobalColor.white)

            # Draw floating content
            if self._selection_content:
                painter.save()
                if self._rotation_angle != 0:
                    center = img_rect.center()
                    painter.translate(center)
                    painter.rotate(self._rotation_angle)
                    painter.translate(-center)
                painter.setOpacity(1.0)
                content = self._get_rendered_content()
                if content:
                    painter.drawImage(self._selection_rect.topLeft(), content)
                painter.restore()

            # Draw border
            painter.setPen(QPen(QColor(0, 120, 255), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(img_rect)

            # Draw handles
            handles = [
                (self._selection_rect.topLeft(), Qt.CursorShape.SizeFDiagCursor),
                (self._selection_rect.topRight(), Qt.CursorShape.SizeBDiagCursor),
                (self._selection_rect.bottomRight(), Qt.CursorShape.SizeFDiagCursor),
                (self._selection_rect.bottomLeft(), Qt.CursorShape.SizeBDiagCursor),
                (
                    QPoint(self._selection_rect.center().x(), self._selection_rect.top()),
                    Qt.CursorShape.SizeVerCursor,
                ),
                (
                    QPoint(self._selection_rect.right(), self._selection_rect.center().y()),
                    Qt.CursorShape.SizeHorCursor,
                ),
                (
                    QPoint(self._selection_rect.center().x(), self._selection_rect.bottom()),
                    Qt.CursorShape.SizeVerCursor,
                ),
                (
                    QPoint(self._selection_rect.left(), self._selection_rect.center().y()),
                    Qt.CursorShape.SizeHorCursor,
                ),
            ]

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 120, 255)))
            for pt, _ in handles:
                rect = QRectF(pt.x() - HANDLE_HALF, pt.y() - HANDLE_HALF, HANDLE_SIZE, HANDLE_SIZE)
                painter.drawRect(rect)

    def key_press_event(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            self.delete_selection()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.reset_selection()
            event.accept()
        elif event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down) and self._has_selection:
            if self._selection_from_canvas and self._move_origin_rect is None:
                self._move_origin_rect = QRect(self._selection_rect)
            dx = (1 if event.key() == Qt.Key.Key_Right else -1) if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right) else 0
            dy = (1 if event.key() == Qt.Key.Key_Down else -1) if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down) else 0
            self._selection_rect.translate(dx, dy)
            self.canvas.update_preview()
            event.accept()

    def deactivate(self) -> None:
        if self._has_selection:
            self.commit_selection()
        super().deactivate()
