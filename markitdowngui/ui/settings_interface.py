from __future__ import annotations

import os

from PySide6.QtCore import QThread, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QGroupBox,
    QScrollArea,
    QTextEdit,
)
from qfluentwidgets import (
    BodyLabel,
    CheckBox,
    ComboBox,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PushButton,
    RadioButton,
    SpinBox,
    TitleLabel,
)

from markitdowngui.core.conversion import (
    ConversionOptions,
    OCR_METHOD_AUTO,
    OCR_METHOD_OPENAI_VISION,
    OCR_METHOD_TESSERACT,
    test_azure_ocr_connection,
)
from markitdowngui.core.openai_endpoint import (
    fetch_openai_compatible_model_ids,
    filter_likely_vision_models,
    test_openai_compatible_endpoint,
)
from markitdowngui.core.settings import SettingsManager
from markitdowngui.core.vision_prompt_defaults import DEFAULT_VISION_SYSTEM_PROMPT
from markitdowngui.ui.dialogs.vision_model_picker import VisionModelPickerDialog


class AzureConnectionTestWorker(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, options: ConversionOptions):
        super().__init__()
        self.options = options

    def run(self) -> None:
        try:
            auth_method = test_azure_ocr_connection(self.options)
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(auth_method)


class OpenAIEndpointTestWorker(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url

    def run(self) -> None:
        try:
            message = test_openai_compatible_endpoint(self.base_url)
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(message)


class OpenAIModelListWorker(QThread):
    succeeded = Signal(list, list)
    failed = Signal(str)

    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url

    def run(self) -> None:
        try:
            all_ids = fetch_openai_compatible_model_ids(self.base_url)
            vision_ids = filter_likely_vision_models(all_ids)
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(vision_ids, all_ids)


class SettingsInterface(QWidget):
    """Settings page shown inside the Fluent navigation."""

    theme_mode_changed = Signal(str)

    _OCR_METHOD_ORDER = (
        OCR_METHOD_AUTO,
        OCR_METHOD_TESSERACT,
        OCR_METHOD_OPENAI_VISION,
    )

    def __init__(self, settings_manager: SettingsManager, translate, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("SettingsInterface")
        self.settings_manager = settings_manager
        self.translate = translate
        self._azure_test_worker: AzureConnectionTestWorker | None = None
        self._openai_test_worker: OpenAIEndpointTestWorker | None = None
        self._openai_models_worker: OpenAIModelListWorker | None = None
        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("SettingsScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root_layout.addWidget(self.scroll_area)

        self.content = QWidget(self.scroll_area)
        self.content.setObjectName("SettingsContent")
        self.scroll_area.setWidget(self.content)

        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(18, 14, 18, 18)
        layout.setSpacing(12)

        layout.addWidget(TitleLabel(self.translate("settings_title")))

        self.general_group = QGroupBox(self.translate("settings_general_group"))
        general_layout = QVBoxLayout(self.general_group)
        general_layout.setSpacing(10)

        general_layout.addWidget(BodyLabel(self.translate("settings_output_format_label")))
        self.output_format_combo = ComboBox()
        self.output_format_combo.addItems([".md"])
        self.output_format_combo.setEnabled(False)
        general_layout.addWidget(self.output_format_combo)

        general_layout.addWidget(BodyLabel(self.translate("settings_output_folder_label")))
        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        self.output_folder_edit = LineEdit()
        self.output_folder_edit.setPlaceholderText(
            self.translate("settings_output_folder_placeholder")
        )
        self.output_folder_edit.editingFinished.connect(self._save_output_folder)
        self.output_folder_button = PushButton(self.translate("browse_button_compact"))
        self.output_folder_button.setIcon(FIF.FOLDER)
        self.output_folder_button.clicked.connect(self._browse_output_folder)
        folder_row.addWidget(self.output_folder_edit, 1)
        folder_row.addWidget(self.output_folder_button)
        general_layout.addLayout(folder_row)

        self.conversion_group = QGroupBox(self.translate("settings_conversion_group"))
        conversion_layout = QVBoxLayout(self.conversion_group)
        conversion_layout.setSpacing(10)

        conversion_layout.addWidget(BodyLabel(self.translate("batch_size_label")))
        self.batch_size_spin = SpinBox()
        self.batch_size_spin.setRange(1, 10)
        self.batch_size_spin.valueChanged.connect(self._save_batch_size)
        conversion_layout.addWidget(self.batch_size_spin)

        conversion_layout.addWidget(BodyLabel(self.translate("header_style_label")))
        self.header_style_combo = ComboBox()
        self.header_style_combo.addItems(
            [
                self.translate("header_style_atx"),
                self.translate("header_style_setext"),
            ]
        )
        self.header_style_combo.currentTextChanged.connect(self._save_format_settings)
        conversion_layout.addWidget(self.header_style_combo)

        conversion_layout.addWidget(BodyLabel(self.translate("table_style_label")))
        self.table_style_combo = ComboBox()
        self.table_style_combo.addItems(
            [
                self.translate("table_style_simple"),
                self.translate("table_style_grid"),
                self.translate("table_style_pipe"),
            ]
        )
        self.table_style_combo.currentTextChanged.connect(self._save_format_settings)
        conversion_layout.addWidget(self.table_style_combo)

        self.ocr_group = QGroupBox(self.translate("settings_ocr_group"))
        ocr_layout = QVBoxLayout(self.ocr_group)
        ocr_layout.setSpacing(10)

        self.ocr_enabled_check = CheckBox(self.translate("settings_ocr_enable_label"))
        self.ocr_enabled_check.setToolTip(self.translate("settings_ocr_enable_tooltip"))
        self.ocr_enabled_check.toggled.connect(self._save_ocr_enabled)
        ocr_layout.addWidget(self.ocr_enabled_check)

        self.ocr_force_pdf_check = CheckBox(
            self.translate("settings_ocr_force_pdf_label")
        )
        self.ocr_force_pdf_check.setToolTip(
            self.translate("settings_ocr_force_pdf_tooltip")
        )
        self.ocr_force_pdf_check.toggled.connect(self._save_ocr_force_pdf)
        ocr_layout.addWidget(self.ocr_force_pdf_check)

        ocr_layout.addWidget(
            BodyLabel(self.translate("settings_ocr_extraction_method_label"))
        )
        self.ocr_method_combo = ComboBox()
        self.ocr_method_combo.addItems(
            [
                self.translate("settings_ocr_method_auto"),
                self.translate("settings_ocr_method_tesseract"),
                self.translate("settings_ocr_method_openai_vision"),
            ]
        )
        self.ocr_method_combo.setToolTip(
            self.translate("settings_ocr_extraction_method_tooltip")
        )
        self.ocr_method_combo.currentIndexChanged.connect(self._save_ocr_method)
        ocr_layout.addWidget(self.ocr_method_combo)

        ocr_layout.addWidget(BodyLabel(self.translate("settings_docintel_label")))
        self.docintel_endpoint_edit = LineEdit()
        self.docintel_endpoint_edit.setPlaceholderText(
            self.translate("settings_docintel_placeholder")
        )
        self.docintel_endpoint_edit.setToolTip(
            self.translate("settings_docintel_tooltip")
        )
        self.docintel_endpoint_edit.editingFinished.connect(
            self._save_docintel_endpoint
        )
        self.docintel_endpoint_edit.textChanged.connect(
            lambda *_args: self._update_azure_test_button_state()
        )
        ocr_layout.addWidget(self.docintel_endpoint_edit)

        azure_test_row = QHBoxLayout()
        azure_test_row.setSpacing(8)
        self.test_azure_button = PushButton(
            self.translate("settings_test_azure_button")
        )
        self.test_azure_button.setIcon(FIF.SYNC)
        self.test_azure_button.setToolTip(
            self.translate("settings_test_azure_tooltip")
        )
        self.test_azure_button.clicked.connect(self._test_azure_connection)
        azure_test_row.addWidget(self.test_azure_button)
        azure_test_row.addStretch(1)
        ocr_layout.addLayout(azure_test_row)

        ocr_layout.addWidget(BodyLabel(self.translate("settings_ocr_language_label")))
        self.ocr_languages_edit = LineEdit()
        self.ocr_languages_edit.setPlaceholderText(
            self.translate("settings_ocr_language_placeholder")
        )
        self.ocr_languages_edit.setToolTip(
            self.translate("settings_ocr_language_tooltip")
        )
        self.ocr_languages_edit.editingFinished.connect(self._save_ocr_languages)
        ocr_layout.addWidget(self.ocr_languages_edit)

        ocr_layout.addWidget(BodyLabel(self.translate("settings_tesseract_path_label")))
        tesseract_row = QHBoxLayout()
        tesseract_row.setSpacing(8)
        self.tesseract_path_edit = LineEdit()
        self.tesseract_path_edit.setPlaceholderText(
            self.translate("settings_tesseract_path_placeholder")
        )
        self.tesseract_path_edit.setToolTip(
            self.translate("settings_tesseract_path_tooltip")
        )
        self.tesseract_path_edit.editingFinished.connect(self._save_tesseract_path)
        self.tesseract_path_button = PushButton(
            self.translate("browse_button_compact")
        )
        self.tesseract_path_button.setIcon(FIF.FOLDER)
        self.tesseract_path_button.clicked.connect(self._browse_tesseract_path)
        tesseract_row.addWidget(self.tesseract_path_edit, 1)
        tesseract_row.addWidget(self.tesseract_path_button)
        ocr_layout.addLayout(tesseract_row)

        self.local_llm_group = QGroupBox(self.translate("settings_local_llm_group"))
        local_llm_layout = QVBoxLayout(self.local_llm_group)
        local_llm_layout.setSpacing(10)

        local_llm_layout.addWidget(BodyLabel(self.translate("settings_llm_url_label")))
        self.llm_url_edit = LineEdit()
        self.llm_url_edit.setPlaceholderText(
            self.translate("settings_llm_url_placeholder")
        )
        self.llm_url_edit.setToolTip(self.translate("settings_llm_url_tooltip"))
        self.llm_url_edit.editingFinished.connect(self._save_llm_url)
        self.llm_url_edit.textChanged.connect(lambda *_: self._update_openai_buttons_state())
        local_llm_layout.addWidget(self.llm_url_edit)

        openai_test_row = QHBoxLayout()
        openai_test_row.setSpacing(8)
        self.test_openai_button = PushButton(
            self.translate("settings_test_openai_button")
        )
        self.test_openai_button.setIcon(FIF.SYNC)
        self.test_openai_button.setToolTip(
            self.translate("settings_test_openai_tooltip")
        )
        self.test_openai_button.clicked.connect(self._test_openai_endpoint)
        openai_test_row.addWidget(self.test_openai_button)
        openai_test_row.addStretch(1)
        local_llm_layout.addLayout(openai_test_row)

        local_llm_layout.addWidget(BodyLabel(self.translate("settings_llm_model_label")))
        model_row = QHBoxLayout()
        model_row.setSpacing(8)
        self.llm_model_edit = LineEdit()
        self.llm_model_edit.setPlaceholderText(
            self.translate("settings_llm_model_placeholder")
        )
        self.llm_model_edit.setToolTip(self.translate("settings_llm_model_tooltip"))
        self.llm_model_edit.editingFinished.connect(self._save_llm_model)
        model_row.addWidget(self.llm_model_edit, 1)
        self.list_vision_models_button = PushButton(
            self.translate("settings_list_vision_models_button")
        )
        self.list_vision_models_button.setIcon(FIF.VIEW)
        self.list_vision_models_button.setToolTip(
            self.translate("settings_list_vision_models_tooltip")
        )
        self.list_vision_models_button.clicked.connect(self._list_vision_models)
        model_row.addWidget(self.list_vision_models_button)
        local_llm_layout.addLayout(model_row)

        vision_prompt_header = QHBoxLayout()
        vision_prompt_header.setSpacing(8)
        vision_prompt_header.addWidget(
            BodyLabel(self.translate("settings_llm_vision_system_label"))
        )
        vision_prompt_header.addStretch(1)
        self.llm_vision_system_restore_btn = PushButton(
            self.translate("settings_llm_vision_system_restore")
        )
        self.llm_vision_system_restore_btn.setIcon(FIF.SYNC)
        self.llm_vision_system_restore_btn.setToolTip(
            self.translate("settings_llm_vision_system_restore_tooltip")
        )
        self.llm_vision_system_restore_btn.clicked.connect(
            self._restore_llm_vision_system_prompt
        )
        vision_prompt_header.addWidget(self.llm_vision_system_restore_btn)
        local_llm_layout.addLayout(vision_prompt_header)

        self.llm_vision_system_edit = QTextEdit()
        self.llm_vision_system_edit.setPlaceholderText(
            self.translate("settings_llm_vision_system_placeholder")
        )
        self.llm_vision_system_edit.setToolTip(
            self.translate("settings_llm_vision_system_tooltip")
        )
        self.llm_vision_system_edit.setMinimumHeight(160)
        self._llm_vision_save_timer = QTimer(self)
        self._llm_vision_save_timer.setSingleShot(True)
        self._llm_vision_save_timer.setInterval(400)
        self._llm_vision_save_timer.timeout.connect(self._flush_llm_vision_system_prompt)
        self.llm_vision_system_edit.textChanged.connect(
            self._on_llm_vision_system_text_changed
        )
        local_llm_layout.addWidget(self.llm_vision_system_edit)

        layout.addWidget(self.local_llm_group)

        self.appearance_group = QGroupBox(self.translate("settings_appearance_group"))
        appearance_layout = QVBoxLayout(self.appearance_group)
        appearance_layout.setSpacing(8)

        self.theme_light = RadioButton(self.translate("theme_light"))
        self.theme_dark = RadioButton(self.translate("theme_dark"))
        self.theme_perfect_dark = RadioButton(self.translate("theme_perfect_dark"))
        self.theme_system = RadioButton(self.translate("theme_system"))
        self.theme_light.toggled.connect(lambda checked: self._save_theme("light", checked))
        self.theme_dark.toggled.connect(lambda checked: self._save_theme("dark", checked))
        self.theme_perfect_dark.toggled.connect(
            lambda checked: self._save_theme("perfect_dark", checked)
        )
        self.theme_system.toggled.connect(lambda checked: self._save_theme("system", checked))

        appearance_layout.addWidget(self.theme_light)
        appearance_layout.addWidget(self.theme_dark)
        appearance_layout.addWidget(self.theme_perfect_dark)
        appearance_layout.addWidget(self.theme_system)

        columns_outer = QHBoxLayout()
        columns_outer.setSpacing(20)
        left_col = QVBoxLayout()
        right_col = QVBoxLayout()
        left_col.setSpacing(14)
        right_col.setSpacing(14)

        left_col.addWidget(self.general_group)
        left_col.addWidget(self.conversion_group)
        left_col.addWidget(self.appearance_group)
        left_col.addStretch(1)

        right_col.addWidget(self.ocr_group)
        right_col.addWidget(self.local_llm_group)
        right_col.addStretch(1)

        columns_outer.addLayout(left_col, 1)
        columns_outer.addLayout(right_col, 1)
        layout.addLayout(columns_outer, 1)
        layout.addStretch(1)

    def _load_settings(self) -> None:
        self.output_format_combo.setCurrentText(
            self.settings_manager.get_default_output_format()
        )
        self.output_folder_edit.setText(self.settings_manager.get_default_output_folder())
        self.batch_size_spin.setValue(self.settings_manager.get_batch_size())

        format_settings = self.settings_manager.get_format_settings()
        self.header_style_combo.setCurrentText(str(format_settings.get("headerStyle", "")))
        self.table_style_combo.setCurrentText(str(format_settings.get("tableStyle", "")))
        self.ocr_enabled_check.setChecked(self.settings_manager.get_ocr_enabled())
        self.ocr_force_pdf_check.setChecked(
            self.settings_manager.get_ocr_force_pdf()
        )
        self.ocr_force_pdf_check.setEnabled(
            self.settings_manager.get_ocr_enabled()
        )
        method = self.settings_manager.get_ocr_method()
        try:
            method_index = self._OCR_METHOD_ORDER.index(method)
        except ValueError:
            method_index = 0
        self.ocr_method_combo.blockSignals(True)
        self.ocr_method_combo.setCurrentIndex(method_index)
        self.ocr_method_combo.blockSignals(False)
        self.docintel_endpoint_edit.setText(
            self.settings_manager.get_docintel_endpoint()
        )
        self._update_azure_test_button_state()
        self.ocr_languages_edit.setText(self.settings_manager.get_ocr_languages())
        self.tesseract_path_edit.setText(self.settings_manager.get_tesseract_path())
        self.llm_url_edit.setText(self.settings_manager.get_llm_base_url())
        self.llm_model_edit.setText(self.settings_manager.get_llm_model())
        self._update_openai_buttons_state()

        self._llm_vision_save_timer.stop()
        self.llm_vision_system_edit.blockSignals(True)
        self.llm_vision_system_edit.setPlainText(
            self.settings_manager.get_llm_vision_system_prompt()
        )
        self.llm_vision_system_edit.blockSignals(False)

        theme_mode = self.settings_manager.get_theme_mode()
        self.theme_light.setChecked(theme_mode == "light")
        self.theme_dark.setChecked(theme_mode == "dark")
        self.theme_perfect_dark.setChecked(theme_mode == "perfect_dark")
        self.theme_system.setChecked(theme_mode == "system")

    def _save_output_folder(self) -> None:
        self.settings_manager.set_default_output_folder(self.output_folder_edit.text().strip())

    def _browse_output_folder(self) -> None:
        start_dir = self.settings_manager.get_default_output_folder()
        if not start_dir or not os.path.isdir(start_dir):
            start_dir = ""
        folder = QFileDialog.getExistingDirectory(
            self, self.translate("settings_output_folder_dialog"), start_dir
        )
        if folder:
            self.output_folder_edit.setText(folder)
            self.settings_manager.set_default_output_folder(folder)

    def _save_batch_size(self, value: int) -> None:
        self.settings_manager.set_batch_size(value)

    def _save_ocr_enabled(self, checked: bool) -> None:
        self.settings_manager.set_ocr_enabled(checked)
        self.ocr_force_pdf_check.setEnabled(checked)

    def _save_ocr_force_pdf(self, checked: bool) -> None:
        self.settings_manager.set_ocr_force_pdf(checked)

    def _save_ocr_method(self, index: int) -> None:
        if index < 0 or index >= len(self._OCR_METHOD_ORDER):
            return
        self.settings_manager.set_ocr_method(self._OCR_METHOD_ORDER[index])

    def _save_docintel_endpoint(self) -> None:
        self.settings_manager.set_docintel_endpoint(
            self.docintel_endpoint_edit.text()
        )
        self._update_azure_test_button_state()

    def _save_ocr_languages(self) -> None:
        self.settings_manager.set_ocr_languages(self.ocr_languages_edit.text())

    def _save_tesseract_path(self) -> None:
        self.settings_manager.set_tesseract_path(self.tesseract_path_edit.text())

    def _save_llm_url(self) -> None:
        self.settings_manager.set_llm_base_url(self.llm_url_edit.text())

    def _save_llm_model(self) -> None:
        self.settings_manager.set_llm_model(self.llm_model_edit.text())

    def _on_llm_vision_system_text_changed(self) -> None:
        self._llm_vision_save_timer.start()

    def _flush_llm_vision_system_prompt(self) -> None:
        self.settings_manager.set_llm_vision_system_prompt(
            self.llm_vision_system_edit.toPlainText()
        )

    def _restore_llm_vision_system_prompt(self) -> None:
        self._llm_vision_save_timer.stop()
        self.llm_vision_system_edit.blockSignals(True)
        self.llm_vision_system_edit.setPlainText(DEFAULT_VISION_SYSTEM_PROMPT)
        self.llm_vision_system_edit.blockSignals(False)
        self.settings_manager.set_llm_vision_system_prompt(
            DEFAULT_VISION_SYSTEM_PROMPT
        )
        InfoBar.success(
            self.translate("settings_llm_vision_system_restored_title"),
            self.translate("settings_llm_vision_system_restored_message"),
            duration=2500,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _browse_tesseract_path(self) -> None:
        start_path = self.settings_manager.get_tesseract_path()
        if start_path and not os.path.exists(start_path):
            start_path = ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translate("settings_tesseract_dialog"),
            start_path,
            self.translate("all_files_filter"),
        )
        if file_path:
            self.tesseract_path_edit.setText(file_path)
            self.settings_manager.set_tesseract_path(file_path)

    def _save_theme(self, mode: str, checked: bool) -> None:
        if not checked:
            return
        self.settings_manager.set_theme_mode(mode)
        self.theme_mode_changed.emit(mode)

    def _save_format_settings(self, *_args) -> None:
        current = self.settings_manager.get_format_settings()
        current["headerStyle"] = self.header_style_combo.currentText()
        current["tableStyle"] = self.table_style_combo.currentText()
        self.settings_manager.save_format_settings(current)

    def _update_azure_test_button_state(self) -> None:
        if self._azure_test_worker is not None:
            return
        self.test_azure_button.setEnabled(
            bool(self.docintel_endpoint_edit.text().strip())
        )

    def _test_azure_connection(self) -> None:
        self._save_docintel_endpoint()
        self.test_azure_button.setEnabled(False)
        self.test_azure_button.setText(
            self.translate("settings_test_azure_in_progress")
        )

        options = ConversionOptions(
            ocr_enabled=self.ocr_enabled_check.isChecked(),
            ocr_method=self.settings_manager.get_ocr_method(),
            docintel_endpoint=self.docintel_endpoint_edit.text(),
            ocr_languages=self.ocr_languages_edit.text(),
            tesseract_path=self.tesseract_path_edit.text(),
            llm_base_url=self.llm_url_edit.text(),
            llm_model=self.llm_model_edit.text(),
            llm_saved_for_auto_ocr=self.settings_manager.is_llm_saved_for_automatic_ocr_chain(),
        )
        worker = AzureConnectionTestWorker(options)
        self._azure_test_worker = worker
        worker.succeeded.connect(self._handle_azure_test_success)
        worker.failed.connect(self._handle_azure_test_failure)
        worker.finished.connect(self._finish_azure_test)
        worker.start()

    def _handle_azure_test_success(self, auth_method: str) -> None:
        auth_label_key = "settings_test_azure_auth_identity"
        if auth_method == "api_key":
            auth_label_key = "settings_test_azure_auth_api_key"

        InfoBar.success(
            self.translate("settings_test_azure_success_title"),
            self.translate("settings_test_azure_success_message").format(
                auth_method=self.translate(auth_label_key)
            ),
            duration=4000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _handle_azure_test_failure(self, error: str) -> None:
        InfoBar.error(
            self.translate("settings_test_azure_failure_title"),
            self.translate("settings_test_azure_failure_message").format(error=error),
            duration=5000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _finish_azure_test(self) -> None:
        if self._azure_test_worker is not None:
            self._azure_test_worker.deleteLater()
            self._azure_test_worker = None
        self.test_azure_button.setText(self.translate("settings_test_azure_button"))
        self._update_azure_test_button_state()

    def _update_openai_buttons_state(self) -> None:
        if self._openai_test_worker is not None or self._openai_models_worker is not None:
            return
        url_ok = bool(self.llm_url_edit.text().strip())
        self.test_openai_button.setEnabled(url_ok)
        self.list_vision_models_button.setEnabled(url_ok)

    def _test_openai_endpoint(self) -> None:
        self._save_llm_url()
        self._save_llm_model()
        self.test_openai_button.setEnabled(False)
        self.list_vision_models_button.setEnabled(False)
        self.test_openai_button.setText(
            self.translate("settings_test_openai_in_progress")
        )

        worker = OpenAIEndpointTestWorker(self.llm_url_edit.text())
        self._openai_test_worker = worker
        worker.succeeded.connect(self._handle_openai_test_success)
        worker.failed.connect(self._handle_openai_test_failure)
        worker.finished.connect(self._finish_openai_test)
        worker.start()

    def _handle_openai_test_success(self, message: str) -> None:
        InfoBar.success(
            self.translate("settings_test_openai_success_title"),
            self.translate("settings_test_openai_success_message").format(detail=message),
            duration=4000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _handle_openai_test_failure(self, error: str) -> None:
        InfoBar.error(
            self.translate("settings_test_openai_failure_title"),
            self.translate("settings_test_openai_failure_message").format(error=error),
            duration=5000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _finish_openai_test(self) -> None:
        if self._openai_test_worker is not None:
            self._openai_test_worker.deleteLater()
            self._openai_test_worker = None
        self.test_openai_button.setText(self.translate("settings_test_openai_button"))
        self._update_openai_buttons_state()

    def _list_vision_models(self) -> None:
        self._save_llm_url()
        self._save_llm_model()
        self.test_openai_button.setEnabled(False)
        self.list_vision_models_button.setEnabled(False)
        self.list_vision_models_button.setText(
            self.translate("settings_list_vision_models_in_progress")
        )

        worker = OpenAIModelListWorker(self.llm_url_edit.text())
        self._openai_models_worker = worker
        worker.succeeded.connect(self._handle_models_list_success)
        worker.failed.connect(self._handle_models_list_failure)
        worker.finished.connect(self._finish_models_list)
        worker.start()

    def _handle_models_list_success(self, vision_ids: list, all_ids: list) -> None:
        if not all_ids:
            InfoBar.warning(
                self.translate("settings_list_models_empty_title"),
                self.translate("settings_list_models_empty_message"),
                duration=5000,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self,
            )
            return

        dialog = VisionModelPickerDialog(
            vision_model_ids=vision_ids,
            all_model_ids=all_ids,
            translate=self.translate,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            model_id = dialog.selected_model_id().strip()
            if model_id:
                self.llm_model_edit.setText(model_id)
                self._save_llm_model()

    def _handle_models_list_failure(self, error: str) -> None:
        InfoBar.error(
            self.translate("settings_list_models_failure_title"),
            self.translate("settings_list_models_failure_message").format(error=error),
            duration=5000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _finish_models_list(self) -> None:
        if self._openai_models_worker is not None:
            self._openai_models_worker.deleteLater()
            self._openai_models_worker = None
        self.list_vision_models_button.setText(
            self.translate("settings_list_vision_models_button")
        )
        self._update_openai_buttons_state()
