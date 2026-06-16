from PySide6.QtGui import QImage


class UndoManager:
    def __init__(self, max_states: int = 100):
        self._undo_stack: list[QImage] = []
        self._redo_stack: list[QImage] = []
        self._max_states = max_states
        self._saved_state_index: int | None = None
        self._clean_index: int | None = None

    def push_state(self, image: QImage) -> None:
        snapshot = image.copy()
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._max_states:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self, current_image: QImage) -> QImage | None:
        if not self._undo_stack:
            return None
        self._redo_stack.append(current_image.copy())
        return self._undo_stack.pop()

    def redo(self, current_image: QImage) -> QImage | None:
        if not self._redo_stack:
            return None
        self._undo_stack.append(current_image.copy())
        return self._redo_stack.pop()

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._saved_state_index = None
        self._clean_index = None

    def mark_saved(self) -> None:
        self._saved_state_index = len(self._undo_stack)

    def is_dirty(self) -> bool:
        return len(self._undo_stack) != self._saved_state_index
