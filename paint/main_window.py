from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QColor, QFont, QFontDatabase, QKeySequence, QTransform
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from paint.canvas.canvas_widget import CanvasWidget
from paint.dialogs.properties_dialog import PropertiesDialog
from paint.dialogs.resize_dialog import ResizeDialog
from paint.services.clipboard_service import ClipboardService
from paint.services.file_service import FileService
from paint.tools.brush_tool import BrushTool
from paint.tools.color_picker_tool import ColorPickerTool
from paint.tools.eraser_tool import EraserTool
from paint.tools.fill_tool import FillTool
from paint.tools.magnifier_tool import MagnifierTool
from paint.tools.pencil_tool import PencilTool
from paint.tools.selection_tool import SelectionTool
from paint.tools.shape_tools import (
    FILL_BOTH,
    FILL_FILL,
    FILL_OUTLINE,
    STROKE_DASHED,
    STROKE_DOTTED,
    STROKE_SOLID,
    CurveTool,
    EllipseTool,
    LineTool,
    PolygonTool,
    RectangleTool,
    RoundedRectTool,
)
from paint.tools.text_tool import TextTool
from paint.widgets.color_palette import ColorPalette
from paint.widgets.rulers import HRuler, VRuler
from paint.widgets.size_selector import SizeSelector
from paint.widgets.thumbnail_window import ThumbnailWindow
from paint.widgets.tool_palette import ToolPalette


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Paint")
        self.resize(1280, 800)

        self._file_service = FileService()
        self._clipboard_service = ClipboardService()

        self._recent_files: list[str] = []
        self._fullscreen = False
        self._show_thumbnail = False
        self._show_rulers = False



        self._thumbnail_window: ThumbnailWindow | None = None
        self._active_shape_fill = FILL_OUTLINE
        self._active_stroke_style = STROKE_SOLID

        self._setup_canvas()
        self._setup_tools()
        self._setup_widgets()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_toolbar_menu()
        self._setup_statusbar()

    def _setup_canvas(self) -> None:
        self.canvas = CanvasWidget()
        self.canvas.color1_changed.connect(self._on_color1_changed)
        self.canvas.color2_changed.connect(self._on_color2_changed)

        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._h_ruler = HRuler()
        self._v_ruler = VRuler()
        self._h_ruler.setVisible(False)
        self._v_ruler.setVisible(False)

        ruler_vlayout = QVBoxLayout()
        ruler_vlayout.setContentsMargins(0, 0, 0, 0)
        ruler_vlayout.setSpacing(0)

        corner = QFrame()
        corner.setFixedSize(20, 20)
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)
        top_layout.addWidget(corner)
        top_layout.addWidget(self._h_ruler)
        ruler_vlayout.addLayout(top_layout)

        mid_layout = QHBoxLayout()
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.setSpacing(0)
        mid_layout.addWidget(self._v_ruler)
        mid_layout.addWidget(scroll)
        ruler_vlayout.addLayout(mid_layout)

        central = QWidget()
        central.setLayout(ruler_vlayout)
        self.setCentralWidget(central)

        self.canvas.zoom_changed.connect(self._on_zoom_changed)
        self.canvas.status_coords.connect(self._update_status)

    def _setup_tools(self) -> None:
        pencil = PencilTool(self.canvas)
        brush = BrushTool(self.canvas)
        eraser = EraserTool(self.canvas)
        fill = FillTool(self.canvas)
        picker = ColorPickerTool(self.canvas)
        magnifier = MagnifierTool(self.canvas)
        select_rect = SelectionTool(self.canvas, SelectionTool.MODE_RECT)
        select_free = SelectionTool(self.canvas, SelectionTool.MODE_FREEFORM)
        text = TextTool(self.canvas)
        line = LineTool(self.canvas)
        curve = CurveTool(self.canvas)
        rect = RectangleTool(self.canvas)
        ellipse = EllipseTool(self.canvas)
        rounded_rect = RoundedRectTool(self.canvas)
        polygon = PolygonTool(self.canvas)

        tools = {
            "pencil": pencil,
            "brush": brush,
            "eraser": eraser,
            "fill": fill,
            "picker": picker,
            "magnifier": magnifier,
            "select_rect": select_rect,
            "select_freeform": select_free,
            "text": text,
            "line": line,
            "curve": curve,
            "rectangle": rect,
            "ellipse": ellipse,
            "rounded_rect": rounded_rect,
            "polygon": polygon,
        }

        for name, tool in tools.items():
            self.canvas.register_tool(name, tool)

        self.canvas.set_active_tool("pencil")

        text.editing_started.connect(self._on_text_editing_started)
        text.editing_finished.connect(self._on_text_editing_finished)

        self._select_rect_tool = select_rect
        self._select_free_tool = select_free
        self._text_tool = text
        self._pencil_tool = pencil
        self._brush_tool = brush
        self._eraser_tool = eraser
        self._line_tool = line
        self._curve_tool = curve
        self._rect_tool = rect
        self._ellipse_tool = ellipse
        self._rounded_rect_tool = rounded_rect
        self._polygon_tool = polygon

    def _setup_widgets(self) -> None:
        self._tool_palette = ToolPalette()
        self._tool_palette.tool_selected.connect(self._on_tool_selected)
        self._tool_palette.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._color_palette = ColorPalette()
        self._color_palette.color1_changed.connect(lambda c: setattr(self.canvas, "color1", c))
        self._color_palette.color2_changed.connect(lambda c: setattr(self.canvas, "color2", c))
        self._color_palette.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self._size_selector = SizeSelector()
        self._size_selector.size_changed.connect(self._on_size_changed)

        self._stroke_style_combo = QComboBox()
        self._stroke_style_combo.addItem("Solid")
        self._stroke_style_combo.addItem("Dashed")
        self._stroke_style_combo.addItem("Dotted")
        self._stroke_style_combo.currentIndexChanged.connect(self._on_stroke_style_changed)

        self._fill_mode_combo = QComboBox()
        self._fill_mode_combo.addItem("Outline")
        self._fill_mode_combo.addItem("Fill")
        self._fill_mode_combo.addItem("Outline + Fill")
        self._fill_mode_combo.currentIndexChanged.connect(self._on_fill_mode_changed)

    def _on_tool_selected(self, tool_name: str) -> None:
        self.canvas.set_active_tool(tool_name)

        shape_tools = {"line", "curve", "rectangle", "ellipse", "rounded_rect", "polygon"}
        size_tools = {"pencil", "brush", "eraser", "line"} | shape_tools
        select_tools = {"select_rect", "select_freeform"}

        self._size_selector.setVisible(tool_name in size_tools)

        show_fill = tool_name in shape_tools
        self._fill_mode_combo.setVisible(show_fill)
        self._stroke_style_combo.setVisible(show_fill)
        self._fill_mode_label.setVisible(show_fill)

        self._transparent_select_check.setVisible(tool_name in select_tools)

        # Propagate current UI settings to the newly selected tool
        tool = self.canvas._active_tool
        if tool:
            if hasattr(tool, "set_size"):
                tool.set_size(self._size_selector.current_size())
            if hasattr(tool, "set_fill_mode"):
                tool.set_fill_mode(self._active_shape_fill)
            if hasattr(tool, "set_stroke_style"):
                tool.set_stroke_style(self._active_stroke_style)

        if tool_name == "text":
            if self._text_tool and self._text_tool.is_editing():
                self._show_text_toolbar()
        else:
            if self._text_tool and self._text_tool.is_editing():
                self._text_tool.commit()
            self._hide_text_toolbar()

    def _on_size_changed(self, size: int) -> None:
        self.canvas._tool_size = size
        tool = self.canvas._active_tool
        if tool and hasattr(tool, "set_size"):
            tool.set_size(size)

    def _on_stroke_style_changed(self, index: int) -> None:
        styles = [STROKE_SOLID, STROKE_DASHED, STROKE_DOTTED]
        self._active_stroke_style = styles[index] if index < len(styles) else STROKE_SOLID
        tool = self.canvas._active_tool
        if tool and hasattr(tool, "set_stroke_style"):
            tool.set_stroke_style(self._active_stroke_style)

    def _on_fill_mode_changed(self, index: int) -> None:
        modes = [FILL_OUTLINE, FILL_FILL, FILL_BOTH]
        self._active_shape_fill = modes[index] if index < len(modes) else FILL_OUTLINE
        tool = self.canvas._active_tool
        if tool and hasattr(tool, "set_fill_mode"):
            tool.set_fill_mode(self._active_shape_fill)

    def _setup_menus(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        self._add_action(file_menu, "&New", "Ctrl+N", self._file_new)
        self._add_action(file_menu, "&Open...", "Ctrl+O", self._file_open)
        file_menu.addSeparator()
        self._add_action(file_menu, "&Save", "Ctrl+S", self._file_save)
        self._add_action(file_menu, "Save &As...", "Ctrl+Shift+S", self._file_save_as)
        file_menu.addSeparator()

        self._recent_menu = file_menu.addMenu("Recent Files")
        self._update_recent_menu()

        file_menu.addSeparator()
        self._add_action(file_menu, "E&xit", None, self.close)

        edit_menu = menubar.addMenu("&Edit")
        self._undo_action = self._add_action(edit_menu, "&Undo", "Ctrl+Z", self._edit_undo)
        self._redo_action = self._add_action(edit_menu, "&Redo", "Ctrl+Y", self._edit_redo)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "&Copy", "Ctrl+C", self._edit_copy)
        self._add_action(edit_menu, "Cu&t", "Ctrl+X", self._edit_cut)
        self._add_action(edit_menu, "&Paste", "Ctrl+V", self._edit_paste)
        self._add_action(edit_menu, "Paste From File...", None, self._edit_paste_from_file)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Select &All", "Ctrl+A", self._edit_select_all)
        self._add_action(edit_menu, "&Invert Selection", None, self._edit_invert_selection)
        self._add_action(edit_menu, "&Delete", "Delete", self._edit_delete)

        self._view_menu = menubar.addMenu("&View")
        self._add_action(self._view_menu, "Zoom &In", None, lambda: self.canvas.zoom_in())
        self._add_action(self._view_menu, "Zoom &Out", None, lambda: self.canvas.zoom_out())
        self._add_action(self._view_menu, "Actual &Pixels", None, self.canvas.actual_pixels)
        self._add_action(self._view_menu, "Fit to &Window", None, self.canvas.fit_to_window)
        self._view_menu.addSeparator()
        self._add_action(self._view_menu, "&Full Screen", "F11", self._toggle_fullscreen)
        self._view_menu.addSeparator()
        self._add_action(self._view_menu, "&Thumbnail", None, self._toggle_thumbnail)
        self._add_action(self._view_menu, "&Rulers", None, self._toggle_rulers)

        image_menu = menubar.addMenu("&Image")
        self._add_action(image_menu, "&Flip Horizontal", None, self._image_flip_h)
        self._add_action(image_menu, "Flip &Vertical", None, self._image_flip_v)
        image_menu.addSeparator()
        self._add_action(image_menu, "&Rotate 90\xb0 CW", None, self._image_rotate_cw)
        self._add_action(image_menu, "Rotate 90\xb0 C&CW", None, self._image_rotate_ccw)
        self._add_action(image_menu, "Rotate &180\xb0", None, self._image_rotate_180)
        image_menu.addSeparator()
        self._add_action(image_menu, "&Resize/Skew...", "Ctrl+W", self._image_resize)
        self._add_action(image_menu, "&Crop", None, self._image_crop)
        image_menu.addSeparator()
        self._add_action(image_menu, "&Properties...", "Ctrl+E", self._image_properties)

        colors_menu = menubar.addMenu("&Colors")
        self._add_action(colors_menu, "Edit Colors...", None, self._color_edit)

        help_menu = menubar.addMenu("&Help")
        self._add_action(help_menu, "&About Paint", None, self._show_about)

    def _add_action(self, menu: QMenu, text: str, shortcut: str | None, callback) -> QAction:
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(callback)
        menu.addAction(action)
        return action

    def _update_status(
        self, x: int, y: int, sel_w: int, sel_h: int, img_w: int, img_h: int, zoom: float
    ) -> None:
        self._coords_label.setText(f"{x:4d},{y:4d}")
        if sel_w > 0 and sel_h > 0:
            self._selection_label.setText(f"  {sel_w}\xd7{sel_h}")
        else:
            self._selection_label.setText("")
        self._size_label.setText(f"  {img_w}\xd7{img_h}")
        self._zoom_label.setText(f"  {int(zoom)}%")

    def _on_zoom_changed(self, zoom: int) -> None:
        if self._thumbnail_window and self._thumbnail_window.isVisible():
            viewport = self.canvas.viewport().rect()
            self._thumbnail_window.set_viewport(viewport)

    def _on_color1_changed(self, color: QColor) -> None:
        self._color_palette.color1 = color

    def _on_color2_changed(self, color: QColor) -> None:
        self._color_palette.color2 = color

    def _setup_toolbar(self) -> None:
        tb = QToolBar("Tools")
        tb.setObjectName("main_toolbar")
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)
        self._main_toolbar = tb

        layout = QHBoxLayout()
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        # Undo / Redo buttons
        self._undo_btn = QToolButton()
        self._undo_btn.setText("\u21a9")
        self._undo_btn.setToolTip("Undo (Ctrl+Z)")
        self._undo_btn.clicked.connect(self._edit_undo)
        layout.addWidget(self._undo_btn)

        self._redo_btn = QToolButton()
        self._redo_btn.setText("\u21aa")
        self._redo_btn.setToolTip("Redo (Ctrl+Y)")
        self._redo_btn.clicked.connect(self._edit_redo)
        layout.addWidget(self._redo_btn)

        sep_ur = QFrame()
        sep_ur.setFrameShape(QFrame.Shape.VLine)
        sep_ur.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep_ur)

        layout.addWidget(self._tool_palette)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep1)

        self._size_selector.setFixedWidth(80)
        layout.addWidget(self._size_selector)

        # Inline text toolbar — shown only when editing text (replaces size selector)
        self._text_inline_frame = QFrame()
        self._text_inline_frame.setVisible(False)
        text_grid = QGridLayout(self._text_inline_frame)
        text_grid.setContentsMargins(0, 0, 0, 0)
        text_grid.setSpacing(4)

        self._text_font_combo = QComboBox()
        self._text_font_combo.addItems(QFontDatabase().families())
        self._text_font_combo.setCurrentText("Sans")
        self._text_font_combo.setMinimumWidth(120)
        self._text_font_combo.currentTextChanged.connect(self._on_text_font_changed)
        text_grid.addWidget(self._text_font_combo, 0, 0, 1, 4)

        size_label = QLabel("Size:")
        text_grid.addWidget(size_label, 1, 0)
        self._text_size_spin = QSpinBox()
        self._text_size_spin.setRange(1, 200)
        self._text_size_spin.setValue(12)
        self._text_size_spin.valueChanged.connect(self._on_text_font_changed)
        text_grid.addWidget(self._text_size_spin, 1, 1)

        self._text_bold_btn = QToolButton()
        self._text_bold_btn.setText("B")
        self._text_bold_btn.setCheckable(True)
        self._text_bold_btn.setToolTip("Bold")
        self._text_bold_btn.toggled.connect(self._text_tool.set_bold)
        text_grid.addWidget(self._text_bold_btn, 2, 0)

        self._text_italic_btn = QToolButton()
        self._text_italic_btn.setText("I")
        self._text_italic_btn.setCheckable(True)
        self._text_italic_btn.setToolTip("Italic")
        self._text_italic_btn.toggled.connect(self._text_tool.set_italic)
        text_grid.addWidget(self._text_italic_btn, 2, 1)

        self._text_underline_btn = QToolButton()
        self._text_underline_btn.setText("U")
        self._text_underline_btn.setCheckable(True)
        self._text_underline_btn.setToolTip("Underline")
        self._text_underline_btn.toggled.connect(self._text_tool.set_underline)
        text_grid.addWidget(self._text_underline_btn, 2, 2)

        self._text_strikeout_btn = QToolButton()
        self._text_strikeout_btn.setText("S")
        self._text_strikeout_btn.setCheckable(True)
        self._text_strikeout_btn.setToolTip("Strikeout")
        self._text_strikeout_btn.toggled.connect(self._text_tool.set_strikeout)
        text_grid.addWidget(self._text_strikeout_btn, 2, 3)

        self._text_bg_check = QCheckBox("Transparent")
        self._text_bg_check.setChecked(True)
        self._text_bg_check.toggled.connect(self._on_text_bg_mode)
        text_grid.addWidget(self._text_bg_check, 3, 0, 1, 4)

        layout.addWidget(self._text_inline_frame)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep2)

        fill_frame = QWidget()
        fill_layout = QHBoxLayout(fill_frame)
        fill_layout.setContentsMargins(0, 0, 0, 0)
        fill_layout.setSpacing(4)
        self._fill_mode_label = QLabel("Fill:")
        fill_layout.addWidget(self._fill_mode_label)
        self._fill_mode_combo.setFixedWidth(100)
        fill_layout.addWidget(self._fill_mode_combo)
        self._stroke_style_combo.setFixedWidth(80)
        fill_layout.addWidget(self._stroke_style_combo)
        self._fill_mode_label.setVisible(False)
        self._fill_mode_combo.setVisible(False)
        self._stroke_style_combo.setVisible(False)
        layout.addWidget(fill_frame)

        # Transparent selection checkbox — shown only when a selection tool is active
        self._transparent_select_check = QCheckBox("Transparent selection")
        self._transparent_select_check.setVisible(False)
        self._transparent_select_check.toggled.connect(self._on_transparent_select_toggled)
        layout.addWidget(self._transparent_select_check)

        layout.addStretch()

        layout.addWidget(self._color_palette)

        container = QWidget()
        container.setLayout(layout)
        tb.addWidget(container)

    def _setup_toolbar_menu(self) -> None:
        toolbars_menu = self._view_menu.addMenu("Toolbars")
        toolbars_menu.addAction(self._main_toolbar.toggleViewAction())

    def _setup_statusbar(self) -> None:
        sb = self.statusBar()
        self._coords_label = QLabel("     0,   0")
        self._selection_label = QLabel("")
        self._size_label = QLabel("  800\xd7600")
        self._zoom_label = QLabel("  100%")
        sb.addWidget(self._coords_label)
        sb.addWidget(self._selection_label)
        sb.addPermanentWidget(self._size_label)
        sb.addPermanentWidget(self._zoom_label)

    def _show_text_toolbar(self) -> None:
        self._text_inline_frame.setVisible(True)
        self._size_selector.setVisible(False)

    def _hide_text_toolbar(self) -> None:
        self._text_inline_frame.setVisible(False)
        tool_name = self._tool_palette.active_tool
        size_tools = {"pencil", "brush", "eraser", "line", "curve", "rectangle", "ellipse", "rounded_rect", "polygon"}
        self._size_selector.setVisible(tool_name in size_tools)

    def _on_text_editing_started(self) -> None:
        self._show_text_toolbar()

    def _on_text_editing_finished(self) -> None:
        self._hide_text_toolbar()

    def _on_text_font_changed(self) -> None:
        font = QFont(self._text_font_combo.currentText(), self._text_size_spin.value())
        if self._text_tool:
            self._text_tool.set_font(font)
        self.canvas.setFocus()

    def _on_transparent_select_toggled(self, checked: bool) -> None:
        self._select_rect_tool.set_transparent(checked)
        self._select_free_tool.set_transparent(checked)

    def _on_text_bg_mode(self, checked: bool) -> None:
        if self._text_tool:
            self._text_tool.set_background_mode("transparent" if checked else "opaque")

    def _toggle_fullscreen(self) -> None:
        self._fullscreen = not self._fullscreen
        if self._fullscreen:
            self.showFullScreen()
            self.menuBar().hide()
            self.statusBar().hide()
            for tb in self.findChildren(QToolBar):
                tb.hide()
        else:
            self.showNormal()
            self.menuBar().show()
            self.statusBar().show()
            for tb in self.findChildren(QToolBar):
                tb.show()

    def _toggle_thumbnail(self) -> None:
        self._show_thumbnail = not self._show_thumbnail
        if self._show_thumbnail:
            if self._thumbnail_window is None:
                self._thumbnail_window = ThumbnailWindow()
            self._thumbnail_window.set_image(self.canvas.image())
            self._thumbnail_window.show()
        else:
            if self._thumbnail_window:
                self._thumbnail_window.hide()

    def _toggle_rulers(self) -> None:
        self._show_rulers = not self._show_rulers
        self._h_ruler.setVisible(self._show_rulers)
        self._v_ruler.setVisible(self._show_rulers)

    def _file_new(self) -> None:
        if self._maybe_save():
            self.canvas.new_image()

    def _file_open(self) -> None:
        if self._maybe_save():
            image = self._file_service.open_image(self)
            if image is not None:
                self.canvas.load_image(image)

    def _file_save(self) -> bool:
        path = self.canvas.file_path()
        if path:
            result = self._file_service.save_image(self, self.canvas.image(), path)
            if result:
                self.canvas.set_file_path(result)
                return True
        return self._file_save_as()

    def _file_save_as(self) -> bool:
        result = self._file_service.save_image(self, self.canvas.image())
        if result:
            self.canvas.set_file_path(result)
            self._add_recent_file(result)
            return True
        return False

    def _edit_undo(self) -> None:
        self.canvas.undo()

    def _edit_redo(self) -> None:
        self.canvas.redo()

    def _edit_copy(self) -> None:
        image = self._select_rect_tool.copy_selection()
        if image is None:
            image = self.canvas.image().copy()
        self._clipboard_service.copy_image(image)

    def _edit_cut(self) -> None:
        image = self._select_rect_tool.cut_selection()
        if image:
            self._clipboard_service.copy_image(image)
            self.canvas.commit_drawing()

    def _edit_paste(self) -> None:
        image = self._clipboard_service.paste_image()
        if image is not None:
            self.canvas.set_active_tool("select_rect")
            self._tool_palette.set_active_tool("select_rect")
            self._select_rect_tool.paste_selection(image)

    def _edit_paste_from_file(self) -> None:
        image = self._file_service.open_image(self)
        if image is not None:
            self.canvas.set_active_tool("select_rect")
            self._tool_palette.set_active_tool("select_rect")
            self._select_rect_tool.paste_selection(image)

    def _edit_select_all(self) -> None:
        self.canvas.set_active_tool("select_rect")
        self._tool_palette.set_active_tool("select_rect")
        self._select_rect_tool.select_all()

    def _edit_invert_selection(self) -> None:
        self._select_rect_tool.invert_selection()

    def _edit_delete(self) -> None:
        self._select_rect_tool.delete_selection()

    def _image_flip_h(self) -> None:
        self.canvas.set_active_tool("pencil")
        img = self.canvas.image().copy()
        img = img.mirrored(True, False)
        self.canvas.set_image_direct(img)
        self.canvas._undo.push_state(self.canvas.image().copy())

    def _image_flip_v(self) -> None:
        self.canvas.set_active_tool("pencil")
        img = self.canvas.image().copy()
        img = img.mirrored(False, True)
        self.canvas.set_image_direct(img)
        self.canvas._undo.push_state(self.canvas.image().copy())

    def _image_rotate_cw(self) -> None:
        self.canvas.set_active_tool("pencil")
        img = self.canvas.image()
        transform = QTransform().rotate(90)
        result = img.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        self.canvas.set_image_direct(result)
        self.canvas._undo.push_state(self.canvas.image().copy())

    def _image_rotate_ccw(self) -> None:
        self.canvas.set_active_tool("pencil")
        img = self.canvas.image()
        transform = QTransform().rotate(-90)
        result = img.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        self.canvas.set_image_direct(result)
        self.canvas._undo.push_state(self.canvas.image().copy())

    def _image_rotate_180(self) -> None:
        self.canvas.set_active_tool("pencil")
        img = self.canvas.image()
        transform = QTransform().rotate(180)
        result = img.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        self.canvas.set_image_direct(result)
        self.canvas._undo.push_state(self.canvas.image().copy())

    def _image_resize(self) -> None:
        dialog = ResizeDialog(
            self.canvas.image().width(),
            self.canvas.image().height(),
            self,
        )
        if dialog.exec():
            data = dialog.result_data()
            if data:
                self.canvas.set_active_tool("pencil")
                if data["skew_h"] != 0 or data["skew_v"] != 0:
                    img = self.canvas.image()
                    transform = QTransform()
                    transform.shear(
                        data["skew_h"] / 100.0,
                        data["skew_v"] / 100.0,
                    )
                    self.canvas.set_image_direct(
                        img.transformed(transform, Qt.TransformationMode.SmoothTransformation)
                    )
                if (
                    data["width"] != self.canvas.image().width()
                    or data["height"] != self.canvas.image().height()
                ):
                    self.canvas.resize_image(data["width"], data["height"])

    def _image_crop(self) -> None:
        rect = self._select_rect_tool._selection_rect
        if rect.isValid() and rect.width() > 0 and rect.height() > 0:
            self.canvas.crop_image(rect)
            self._select_rect_tool.reset_selection()
        else:
            QMessageBox.information(self, "Crop", "No selection to crop.")

    def _image_properties(self) -> None:
        dialog = PropertiesDialog(
            self.canvas.image().width(),
            self.canvas.image().height(),
            self.canvas.file_path(),
            self,
        )
        if dialog.exec():
            data = dialog.result_data()
            if data:
                if (
                    data["width"] != self.canvas.image().width()
                    or data["height"] != self.canvas.image().height()
                ):
                    self.canvas.resize_image(data["width"], data["height"])

    def _color_edit(self) -> None:
        from PySide6.QtWidgets import QColorDialog

        color = QColorDialog.getColor(self.canvas.color1, self, "Edit Color")
        if color.isValid():
            self.canvas.color1 = color

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About Paint",
            "Paint for Omarchy Linux\n"
            "A classic MS Paint clone for Hyprland/Wayland.\n\n"
            "PySide6 \xb7 Python \xb7 Wayland Native",
        )

    def _add_recent_file(self, path: str | None) -> None:
        if not path:
            return
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._recent_files.insert(0, path)
        if len(self._recent_files) > 4:
            self._recent_files = self._recent_files[:4]
        self._update_recent_menu()

    def _update_recent_menu(self) -> None:
        self._recent_menu.clear()
        for path in self._recent_files:
            action = QAction(path, self)
            action.triggered.connect(lambda checked, p=path: self._open_recent(p))
            self._recent_menu.addAction(action)
        if not self._recent_files:
            self._recent_menu.addAction("(No recent files)").setEnabled(False)

    def _open_recent(self, path: str) -> None:
        if self._maybe_save():
            from PySide6.QtGui import QImage

            image = QImage(path)
            if not image.isNull():
                self.canvas.load_image(image, path)

    def _maybe_save(self) -> bool:
        if not self.canvas.is_dirty():
            return True
        msg = QMessageBox(self)
        msg.setWindowTitle("Paint")
        msg.setText("Do you want to save changes?")
        msg.setInformativeText("Your changes will be lost if you don't save them.")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Save)
        result = msg.exec()

        if result == QMessageBox.StandardButton.Save:
            return self._file_save()
        return result == QMessageBox.StandardButton.Discard

    def closeEvent(self, event) -> None:
        if self._maybe_save():
            event.accept()
        else:
            event.ignore()
