from PySide6.QtCore import (
    QPoint,
    QPointF,
    QRect,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QResizeEvent,
    QTransform,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
)

from paint.canvas.image_buffer import ImageBuffer
from paint.canvas.undo_manager import UndoManager
from paint.services.theme_service import ThemeService

ZOOM_LEVELS = [25, 50, 100, 200, 400, 800, 1600, 3200]


class CanvasWidget(QGraphicsView):
    color1_changed = Signal(QColor)
    color2_changed = Signal(QColor)
    status_coords = Signal(int, int, int, int, int, int, float)
    zoom_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._buffer = ImageBuffer(800, 600)
        self._undo = UndoManager()

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._image_item = QGraphicsPixmapItem()
        self._image_item.setZValue(0)
        self._scene.addItem(self._image_item)

        self._preview_pixmap = QPixmap(800, 600)
        self._preview_pixmap.fill(Qt.GlobalColor.transparent)
        self._preview_item = QGraphicsPixmapItem()
        self._preview_item.setPixmap(self._preview_pixmap)
        self._preview_item.setZValue(2)
        self._scene.addItem(self._preview_item)

        self._selection_overlay_item = QGraphicsPixmapItem()
        self._selection_overlay_item.setZValue(3)
        self._scene.addItem(self._selection_overlay_item)

        self._color1 = QColor(0, 0, 0)
        self._color2 = QColor(255, 255, 255)
        self._tool_size = 1
        self._zoom_level = 100
        self._show_pixel_grid = False
        self._fit_to_window = False
        self._file_path: str | None = None
        self._dirty = False

        self._theme = ThemeService()
        self._panning = False
        self._pan_start = QPoint()

        self._active_tool = None
        self._tools: dict[str, object] = {}

        # Resize handles (canvas edge nubs)
        self._resize_handle_size = 8.0
        self._resize_hover: str | None = None
        self._resize_dragging = False
        self._resize_drag_handle: str | None = None
        self._resize_drag_start_scene = QPointF()
        self._resize_preview_rect: QRect | None = None
        self._update_resize_handles()

        self.setup_view()

        self._undo.push_state(self._buffer.image)
        self.update_image_item()

    def setup_view(self) -> None:
        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.update_background()

    def update_background(self) -> None:
        color = self._theme.workspace_color()
        self.setBackgroundBrush(QBrush(color))

    def _update_resize_handles(self) -> None:
        w = float(self._buffer.width())
        h = float(self._buffer.height())
        half = self._resize_handle_size / 2.0
        self._resize_handles: list[tuple[str, QRectF]] = []
        edges: list[tuple[str, float, float]] = [
            ("top", w / 2.0, 0.0),
            ("bottom", w / 2.0, h),
            ("left", 0.0, h / 2.0),
            ("right", w, h / 2.0),
        ]
        for name, cx, cy in edges:
            r = QRectF(cx - half, cy - half, self._resize_handle_size, self._resize_handle_size)
            self._resize_handles.append((name, r))

    def _resize_handle_at(self, scene_pos: QPointF) -> str | None:
        for name, rect in self._resize_handles:
            if rect.contains(scene_pos):
                return name
        return None

    def _do_resize_to(self, new_rect: QRect) -> None:
        old_rect = QRect(0, 0, self._buffer.width(), self._buffer.height())
        if new_rect == old_rect:
            return
        if new_rect.isEmpty():
            return
        self._undo.push_state(self._buffer.image.copy())
        union = old_rect.united(new_rect)
        if union != old_rect:
            self._buffer.expand_to_rect(union, QColor(Qt.GlobalColor.white))
        if new_rect != union:
            self._buffer.crop(new_rect)
        self._resize_preview(new_rect.width(), new_rect.height())
        self._update_resize_handles()
        self.update_image_item()
        self._dirty = True

    def register_tool(self, name: str, tool) -> None:
        self._tools[name] = tool

    def set_active_tool(self, name: str) -> None:
        if self._active_tool:
            self._active_tool.deactivate()
        self._active_tool = self._tools.get(name)
        if self._active_tool:
            self._active_tool.activate()
            self.setCursor(self._active_tool.cursor())

    @property
    def color1(self) -> QColor:
        return self._color1

    @color1.setter
    def color1(self, color: QColor) -> None:
        new_c = QColor(color)
        if self._color1 == new_c:
            return
        self._color1 = new_c
        self.color1_changed.emit(self._color1)

    @property
    def color2(self) -> QColor:
        return self._color2

    @color2.setter
    def color2(self, color: QColor) -> None:
        new_c = QColor(color)
        if self._color2 == new_c:
            return
        self._color2 = new_c
        self.color2_changed.emit(self._color2)

    def image(self) -> QImage:
        return self._buffer.image

    def set_image_direct(self, image: QImage) -> None:
        self._buffer.image = image
        self._resize_preview(image.width(), image.height())
        self._update_resize_handles()
        self.update_image_item()
        self._dirty = True

    def apply_image(self, image: QImage) -> None:
        self._undo.push_state(self._buffer.image.copy())
        self._buffer.image = image
        self._resize_preview(image.width(), image.height())
        self._update_resize_handles()
        self.update_image_item()
        self._dirty = True

    def _resize_preview(self, w: int, h: int) -> None:
        self._preview_pixmap = QPixmap(w, h)
        self._preview_pixmap.fill(Qt.GlobalColor.transparent)
        self._preview_item.setPixmap(self._preview_pixmap)

    @property
    def preview_pixmap(self) -> QPixmap:
        return self._preview_pixmap

    def update_preview(self) -> None:
        self._preview_item.setPixmap(self._preview_pixmap)
        self._scene.update()
        self.update_selection_overlay()

    def update_image_item(self) -> None:
        pixmap = QPixmap.fromImage(self._buffer.image)
        self._image_item.setPixmap(pixmap)
        self._scene.setSceneRect(QRectF(pixmap.rect()))

        if self._fit_to_window:
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def commit_drawing(self) -> None:
        img = self._buffer.image
        if self._preview_pixmap.isNull():
            return

        self._undo.push_state(img.copy())

        painter = QPainter(img)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.drawPixmap(0, 0, self._preview_pixmap)
        painter.end()

        self._resize_preview(img.width(), img.height())
        self.update_image_item()
        self._dirty = True

    def clear_selection_overlay(self) -> None:
        self._selection_overlay_item.setPixmap(QPixmap())

    def update_selection_overlay(self) -> None:
        pixmap = QPixmap(self._buffer.width(), self._buffer.height())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)

        if self._active_tool:
            self._active_tool.paint_overlay(painter)

        painter.end()
        self._selection_overlay_item.setPixmap(pixmap)

    def map_scene_to_image(self, viewport_pos: QPoint) -> QPoint:
        scene_pt = self.mapToScene(viewport_pos)
        return QPoint(int(scene_pt.x()), int(scene_pt.y()))

    def resize_image(
        self, new_width: int, new_height: int, expand_color: QColor = Qt.GlobalColor.white
    ) -> None:
        self._undo.push_state(self._buffer.image.copy())
        self._buffer.resize(new_width, new_height, expand_color)
        self._resize_preview(new_width, new_height)
        self._update_resize_handles()
        self.update_image_item()
        self._dirty = True

    def crop_image(self, rect: QRect) -> None:
        self._undo.push_state(self._buffer.image.copy())
        self._buffer.crop(rect)
        self._resize_preview(rect.width(), rect.height())
        self._update_resize_handles()
        self.update_image_item()
        self._dirty = True

    def set_zoom(self, zoom_level: int) -> None:
        self._zoom_level = max(25, min(3200, zoom_level))
        factor = self._zoom_level / 100.0
        transform = QTransform()
        transform.scale(factor, factor)
        self.setTransform(transform)
        self.zoom_changed.emit(self._zoom_level)
        self._show_pixel_grid = self._zoom_level >= 400
        self.update()

    def zoom_in(self) -> None:
        current = self._zoom_level
        for z in ZOOM_LEVELS:
            if z > current:
                self.set_zoom(z)
                return
        self.set_zoom(min(3200, current * 2))

    def zoom_out(self) -> None:
        current = self._zoom_level
        for z in reversed(ZOOM_LEVELS):
            if z < current:
                self.set_zoom(z)
                return
        self.set_zoom(max(25, current // 2))

    def zoom_centered(self, scene_pos: QPoint) -> None:
        self.centerOn(self.mapToScene(scene_pos))
        self.zoom_in()

    def zoom_to_selection(self, rect: QRect) -> None:
        if rect.isValid() and not rect.isEmpty():
            self.fitInView(QRectF(rect), Qt.AspectRatioMode.KeepAspectRatio)

    def actual_pixels(self) -> None:
        self.set_zoom(100)

    def fit_to_window(self) -> None:
        self._fit_to_window = True
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def new_image(self, width: int = 800, height: int = 600) -> None:
        self._buffer = ImageBuffer(width, height)
        self._undo.clear()
        self._file_path = None
        self._dirty = False
        self._resize_preview(width, height)
        self._update_resize_handles()
        self.clear_selection_overlay()
        self.update_image_item()
        self._undo.push_state(self._buffer.image.copy())

    def load_image(self, image: QImage, file_path: str | None = None) -> None:
        self._buffer.image = image
        self._undo.clear()
        self._file_path = file_path
        self._dirty = False
        self._resize_preview(image.width(), image.height())
        self._update_resize_handles()
        self.clear_selection_overlay()
        self.update_image_item()
        self._undo.push_state(self._buffer.image.copy())
        self.set_zoom(100)

    def is_dirty(self) -> bool:
        return self._dirty

    def file_path(self) -> str | None:
        return self._file_path

    def set_file_path(self, path: str | None) -> None:
        self._file_path = path

    def undo(self) -> None:
        image = self._undo.undo(self._buffer.image)
        if image:
            self._buffer.image = image
            self._resize_preview(image.width(), image.height())
            self._update_resize_handles()
            self.update_image_item()
            self._dirty = self._undo.is_dirty()

    def redo(self) -> None:
        image = self._undo.redo(self._buffer.image)
        if image:
            self._buffer.image = image
            self._resize_preview(image.width(), image.height())
            self._update_resize_handles()
            self.update_image_item()
            self._dirty = self._undo.is_dirty()

    def can_undo(self) -> bool:
        return self._undo.can_undo()

    def can_redo(self) -> bool:
        return self._undo.can_redo()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def _update_resize_drag(self, scene_pos: QPointF) -> None:
        if self._resize_preview_rect is None:
            return
        handle = self._resize_drag_handle
        bw = self._buffer.width()
        bh = self._buffer.height()
        left, top, right, bottom = 0.0, 0.0, float(bw), float(bh)
        sx, sy = scene_pos.x(), scene_pos.y()

        if handle == "left":
            left = min(sx, right - 1.0)
        elif handle == "right":
            right = max(sx, left + 1.0)
        elif handle == "top":
            top = min(sy, bottom - 1.0)
        elif handle == "bottom":
            bottom = max(sy, top + 1.0)

        new_rect = QRectF(QPointF(left, top), QPointF(right, bottom)).normalized()
        self._resize_preview_rect = QRect(
            int(round(new_rect.x())),
            int(round(new_rect.y())),
            max(1, int(round(new_rect.width()))),
            max(1, int(round(new_rect.height()))),
        )
        self.viewport().update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        scene_pos = self.mapToScene(event.position().toPoint())
        handle = self._resize_handle_at(scene_pos)
        if handle is not None and event.button() == Qt.MouseButton.LeftButton:
            self._resize_dragging = True
            self._resize_drag_handle = handle
            self._resize_drag_start_scene = scene_pos
            self._resize_preview_rect = QRect(
                0, 0, self._buffer.width(), self._buffer.height()
            )
            event.accept()
            return

        if self._active_tool:
            self._active_tool.mouse_press_event(event)

        self.update_selection_overlay()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        scene_pos = self.mapToScene(event.position().toPoint())

        if self._resize_dragging:
            self._update_resize_drag(scene_pos)
            event.accept()
            return

        if self._panning:
            delta = event.position().toPoint() - self._pan_start
            self._pan_start = event.position().toPoint()
            hsb = self.horizontalScrollBar()
            vsb = self.verticalScrollBar()
            hsb.setValue(hsb.value() - delta.x())
            vsb.setValue(vsb.value() - delta.y())
            event.accept()
            return

        handle = self._resize_handle_at(scene_pos)
        if handle != self._resize_hover:
            self._resize_hover = handle
            if handle in ("left", "right"):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif handle in ("top", "bottom"):
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif self._active_tool:
                self.setCursor(self._active_tool.cursor())
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

        if self._active_tool:
            self._active_tool.mouse_move_event(event)

        self.update_selection_overlay()

        image_pos = self.map_scene_to_image(event.position().toPoint())
        self.status_coords.emit(
            image_pos.x(),
            image_pos.y(),
            0,
            0,
            self._buffer.width(),
            self._buffer.height(),
            self._zoom_level,
        )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._resize_dragging:
            if self._resize_preview_rect is not None:
                self._do_resize_to(self._resize_preview_rect)
            self._resize_dragging = False
            self._resize_drag_handle = None
            self._resize_drag_start_scene = QPointF()
            self._resize_preview_rect = None
            if self._active_tool:
                self.setCursor(self._active_tool.cursor())
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            if self._active_tool:
                self.setCursor(self._active_tool.cursor())
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        if self._active_tool:
            self._active_tool.mouse_release_event(event)

        self.update_selection_overlay()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self._active_tool:
            if hasattr(self._active_tool, "mouse_double_click_event"):
                self._active_tool.mouse_double_click_event(event)
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Control:
            return
        if self._active_tool:
            self._active_tool.key_press_event(event)
            self.update_selection_overlay()
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if self._active_tool:
            self._active_tool.key_release_event(event)
        super().keyReleaseEvent(event)

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        # Resize preview outline
        if self._resize_preview_rect is not None:
            pen = QPen(QColor(0, 120, 215), 2.0, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(self._resize_preview_rect))

        # Pixel grid
        if self._show_pixel_grid:
            painter.setPen(QPen(QColor(200, 200, 200, 30), 1))
            factor = self._zoom_level / 100.0
            if factor >= 8:
                scene_rect = self.mapToScene(self.viewport().rect()).boundingRect()
                left = max(0, int(scene_rect.left()))
                top = max(0, int(scene_rect.top()))
                right = min(self._buffer.width(), int(scene_rect.right()) + 1)
                bottom = min(self._buffer.height(), int(scene_rect.bottom()) + 1)

                for x in range(left, right + 1):
                    painter.drawLine(QPointF(x, top), QPointF(x, bottom))
                for y in range(top, bottom + 1):
                    painter.drawLine(QPointF(left, y), QPointF(right, y))

        # Canvas resize handles
        handle_color = QColor(0, 120, 215)
        handle_outline = QColor(0, 80, 160)
        for name, hr in self._resize_handles:
            painter.setBrush(handle_color)
            painter.setPen(QPen(handle_outline, 1.0))
            painter.drawRect(hr)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                    event.acceptProposedAction()
                    return
        super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                image = QImage(path)
                if not image.isNull():
                    from PySide6.QtWidgets import QMessageBox

                    msg = QMessageBox(self)
                    msg.setWindowTitle("Open Image")
                    msg.setText(f"Open {path.split('/')[-1]}?")
                    msg.setInformativeText("Choose an action:")
                    open_btn = msg.addButton("Open", QMessageBox.ButtonRole.ActionRole)
                    insert_btn = msg.addButton(
                        "Insert into canvas", QMessageBox.ButtonRole.ActionRole
                    )
                    msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
                    msg.exec()

                    if msg.clickedButton() == open_btn:
                        self.load_image(image, path)
                    elif msg.clickedButton() == insert_btn:
                        if hasattr(self._active_tool, "paste_selection"):
                            self._active_tool.paste_selection(image)
                    return
        super().dropEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._fit_to_window:
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
