from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QVBoxLayout,
)


class VisionModelPickerDialog(QDialog):
    """Pick a model id from the server list; optional filter for vision-like names."""

    def __init__(
        self,
        *,
        vision_model_ids: list[str],
        all_model_ids: list[str],
        translate,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._translate = translate
        self._vision_ids = list(vision_model_ids)
        self._all_ids = list(all_model_ids)
        self._selected_id = ""

        self.setWindowTitle(self._translate("settings_vision_model_picker_title"))
        self.setMinimumSize(420, 320)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self._hint = QLabel(self._translate("settings_vision_model_picker_hint"))
        self._hint.setWordWrap(True)
        layout.addWidget(self._hint)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        layout.addWidget(self._list, 1)

        self._show_all = QCheckBox(self._translate("settings_vision_model_picker_show_all"))
        show_all_checked = not self._vision_ids and bool(self._all_ids)
        self._show_all.setChecked(show_all_checked)
        self._show_all.toggled.connect(self._repopulate)
        layout.addWidget(self._show_all)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_button = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._list.currentRowChanged.connect(self._update_ok_enabled)
        self._repopulate()

    def _current_source(self) -> list[str]:
        if self._show_all.isChecked():
            return self._all_ids
        return self._vision_ids

    def _repopulate(self) -> None:
        self._list.clear()
        for mid in self._current_source():
            self._list.addItem(mid)
        if self._list.count():
            self._list.setCurrentRow(0)
        self._update_ok_enabled()

    def _update_ok_enabled(self) -> None:
        has_models = self._list.count() > 0
        self._ok_button.setEnabled(has_models and self._list.currentRow() >= 0)

    def _on_accept(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        text = item.text().strip()
        if not text:
            return
        self._selected_id = text
        self.accept()

    def selected_model_id(self) -> str:
        return self._selected_id
