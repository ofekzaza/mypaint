from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFrame, QLabel, QVBoxLayout

TOOL_SIZES = [1, 2, 3, 4, 5, 8, 12, 16, 24]

BRUSH_SIZES = [1, 2, 3, 4, 5, 8, 10, 12, 16, 20, 24, 30, 36, 48, 64]

AIRBRUSH_SIZES = [5, 10, 15, 20, 30, 40, 50, 60, 80, 100]


class SizeSelector(QFrame):
    size_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._sizes = TOOL_SIZES
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        label = QLabel("Size:")
        layout.addWidget(label)

        self._combo = QComboBox()
        self._combo.addItems(str(s) for s in self._sizes)
        self._combo.setCurrentIndex(0)
        self._combo.currentIndexChanged.connect(
            lambda idx: self.size_changed.emit(self._sizes[idx])
        )
        layout.addWidget(self._combo)
        layout.addStretch()

    def set_sizes(self, sizes: list[int]) -> None:
        self._sizes = sizes
        self._combo.clear()
        self._combo.addItems(str(s) for s in self._sizes)

    def current_size(self) -> int:
        return self._sizes[self._combo.currentIndex()] if self._sizes else 1
