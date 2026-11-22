from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from pynput import keyboard
from PySide6.QtCore import QCoreApplication, QThread, Signal
from PySide6.QtCore import Signal as pyqtSignal
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.core.api_language_discovery import LanguageDiscoveryError, fetch_model_languages
from src.utils.config_manager import (
    APP_LANGUAGE_OPTIONS,
    DEFAULT_TRANSCRIPTION_LANGUAGE,
    LANGUAGE_CONFIG_KEY,
    ConfigManager,
)

logger = logging.getLogger("whisper")

_MODIFIER_KEYS: list[Any] = [
    keyboard.Key.cmd,
    keyboard.Key.cmd_l,
    keyboard.Key.cmd_r,
    keyboard.Key.ctrl,
    keyboard.Key.ctrl_l,
    keyboard.Key.ctrl_r,
]


class _HotkeyRecorder(QThread):
    """One-shot pynput listener running in a background thread."""

    finished = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._stop_event = threading.Event()

    def run(self) -> None:
        collected: list[Any] = []

        def _on_press(key: Any) -> None:
            if key in _MODIFIER_KEYS:
                collected.append(key)
            else:
                collected.append(key)
                self._stop_event.set()

        with keyboard.Listener(on_press=_on_press) as listener:
            listener.join(timeout=30)

        if collected:
            formatted = _format_hotkey(collected)
            self.finished.emit(formatted)


def _format_hotkey(keys: list[Any]) -> str:
    """Convert a list of pynput keys to a display string like 'Cmd+Ctrl+X'."""
    key_names: dict[Any, str] = {
        keyboard.Key.cmd: "Cmd",
        keyboard.Key.cmd_l: "Cmd",
        keyboard.Key.cmd_r: "Cmd",
        keyboard.Key.ctrl: "Ctrl",
        keyboard.Key.ctrl_l: "Ctrl",
        keyboard.Key.ctrl_r: "Ctrl",
    }
    parts: list[str] = []
    for key in keys:
        name = key_names.get(key, getattr(key, "char", None) or str(key).replace("Key.", ""))
        if name and name not in parts:
            parts.append(name)
    return "+".join(parts)


class _LanguageDiscoveryWorker(QThread):
    languages_ready = Signal(list)
    failed = Signal(str)

    def __init__(
        self,
        stt_api_url: str,
        model_id: str,
        api_key: str | None,
    ) -> None:
        super().__init__()
        self._stt_api_url = stt_api_url
        self._model_id = model_id
        self._api_key = api_key

    def run(self) -> None:
        try:
            languages = fetch_model_languages(
                self._stt_api_url,
                self._model_id,
                self._api_key,
            )
        except LanguageDiscoveryError as exc:
            self.failed.emit(str(exc))
            return
        self.languages_ready.emit(languages)


class SettingsDialog(QDialog):
    def __init__(
        self,
        config: ConfigManager,
        parent: QWidget | None = None,
        on_saved: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._config: ConfigManager = config
        self._on_saved: Callable[[], None] | None = on_saved

        self.setWindowTitle("Settings")
        self.setModal(True)

        self._api_edit: QLineEdit = QLineEdit()
        self._stt_key_edit: QLineEdit = QLineEdit()
        self._stt_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._llm_api_edit: QLineEdit = QLineEdit()
        self._llm_key_edit: QLineEdit = QLineEdit()
        self._llm_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._model_edit: QLineEdit = QLineEdit()
        self._hotkey_edit: QLineEdit = QLineEdit()
        self._hotkey_edit.setReadOnly(True)
        self._record_button: QPushButton = QPushButton("Record")
        self._auto_insert_check: QCheckBox = QCheckBox()
        self._sample_spin: QSpinBox = QSpinBox()
        self._sample_spin.setRange(8000, 48000)
        self._sample_spin.setSingleStep(1000)
        self._silence_spin: QSpinBox = QSpinBox()
        self._silence_spin.setRange(100, 5000)
        self._silence_spin.setSingleStep(50)
        self._silence_spin.setValue(800)
        self._grammar_check: QCheckBox = QCheckBox()
        self._grammar_edit: QLineEdit = QLineEdit()
        self._quality_combo: QComboBox = QComboBox()
        self._quality_combo.addItems(["fast", "balanced", "accurate"])
        saved_language = self._config.get(LANGUAGE_CONFIG_KEY)
        self._saved_transcription_language: str = str(
            saved_language or DEFAULT_TRANSCRIPTION_LANGUAGE
        )
        self._language_combo: QComboBox = QComboBox()
        saved_label = next(
            (
                label
                for code, label in APP_LANGUAGE_OPTIONS
                if code == self._saved_transcription_language
            ),
            self._saved_transcription_language,
        )
        self._language_combo.addItem(saved_label, self._saved_transcription_language)
        self._language_combo.setEnabled(False)
        self._language_status: QLabel = QLabel("Checking model language capabilities…")
        self._refresh_button: QPushButton = QPushButton("Refresh")
        self._available_languages: list[str] = []
        self._language_discovery_succeeded: bool = False
        self._language_worker: _LanguageDiscoveryWorker | None = None
        self._voice_commands_check: QCheckBox = QCheckBox()
        self._recording_label: QLabel = QLabel("")
        self._is_recording_flag: bool = False

        # Keep explicit references to all child widgets to prevent PySide6 + Python 3.14
        # Shiboken GC bug where C++ objects get deleted prematurely.
        self._widget_refs: list[QWidget] = [
            self._api_edit,
            self._stt_key_edit,
            self._llm_api_edit,
            self._llm_key_edit,
            self._model_edit,
            self._hotkey_edit,
            self._record_button,
            self._auto_insert_check,
            self._sample_spin,
            self._silence_spin,
            self._grammar_check,
            self._grammar_edit,
            self._quality_combo,
            self._language_combo,
            self._language_status,
            self._refresh_button,
            self._voice_commands_check,
            self._recording_label,
        ]

        self._setup_ui()
        self._populate_widgets()

        self._record_button.clicked.connect(self._record_hotkey)
        self._language_combo.currentIndexChanged.connect(self._on_language_selection_changed)
        self._refresh_button.clicked.connect(self._start_language_discovery)
        self.accepted.connect(self._save)
        self.rejected.connect(self._cancel)
        self._start_language_discovery()

    def _setup_ui(self) -> None:
        """Build the settings dialog using Qt layouts for proper formatting."""
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self._build_stt_group())
        main_layout.addWidget(self._build_llm_group())
        main_layout.addWidget(self._build_hotkey_group())
        main_layout.addWidget(self._build_prefs_group())

        # Spacer pushes OK/Cancel to bottom
        main_layout.addStretch()

        # OK/Cancel buttons
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        main_layout.addWidget(self._button_box)

        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

        # Store reference to prevent GC
        self._widget_refs.append(self._button_box)

    @staticmethod
    def _add_wide_row(form: QFormLayout, label: str, widget: QWidget) -> None:
        """Add a form row whose field expands horizontally."""
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        form.addRow(label, widget)

    def _build_stt_group(self) -> QGroupBox:
        """STT Server section: transcription URL, its API key, model, quality."""
        group = QGroupBox("STT Server")
        form = QFormLayout(group)
        self._add_wide_row(form, "API &URL:", self._api_edit)
        self._add_wide_row(form, "API K&ey:", self._stt_key_edit)
        self._add_wide_row(form, "&Model Name:", self._model_edit)
        self._add_wide_row(form, "Model &Quality:", self._quality_combo)
        self._add_wide_row(form, "&Language:", self._language_combo)
        form.addRow(self._refresh_button)
        form.addRow(self._language_status)
        return group

    def _build_llm_group(self) -> QGroupBox:
        """LLM Server section: grammar-check URL, its API key, model, toggle."""
        group = QGroupBox("LLM Server")
        form = QFormLayout(group)
        self._add_wide_row(form, "LLM &URL:", self._llm_api_edit)
        self._add_wide_row(form, "LLM Ke&y:", self._llm_key_edit)
        self._add_wide_row(form, "&Grammar Model:", self._grammar_edit)
        self._grammar_check.setText("Enable grammar checking")
        form.addRow(self._grammar_check)
        return group

    def _build_hotkey_group(self) -> QGroupBox:
        """Hotkey section: recorded combo plus record button."""
        group = QGroupBox("Hotkey")
        layout = QHBoxLayout(group)
        self._hotkey_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._recording_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self._recording_label.setVisible(False)
        layout.addWidget(QLabel("Custom Hotkey:"))
        layout.addWidget(self._hotkey_edit)
        layout.addWidget(self._recording_label, stretch=1)
        layout.addWidget(self._record_button)
        return group

    def _build_prefs_group(self) -> QGroupBox:
        """Preferences: insertion behavior, capture tuning, voice commands."""
        group = QGroupBox("Preferences")
        form = QFormLayout(group)
        self._auto_insert_check.setText("Auto-insert after transcription")
        form.addRow(self._auto_insert_check)
        self._add_wide_row(form, "&Sample Rate (Hz):", self._sample_spin)
        self._add_wide_row(form, "&Silence Threshold (ms):", self._silence_spin)
        self._voice_commands_check.setText("Enable voice commands")
        form.addRow(self._voice_commands_check)
        return group

    def _populate_widgets(self) -> None:
        self._api_edit.setText(str(self._config.get("stt_api_url") or ""))
        self._stt_key_edit.setText(str(self._config.get("stt_api_key") or ""))
        self._llm_api_edit.setText(str(self._config.get("llm_api_url") or ""))
        self._llm_key_edit.setText(str(self._config.get("llm_api_key") or ""))
        self._model_edit.setText(str(self._config.get("model_name") or ""))
        self._hotkey_edit.setText(str(self._config.get("hotkey") or ""))
        self._auto_insert_check.setChecked(bool(self._config.get("auto_insert")))
        self._sample_spin.setValue(int(self._config.get("sample_rate") or 16000))
        self._silence_spin.setValue(int(self._config.get("silence_threshold_ms") or 800))
        self._grammar_check.setChecked(bool(self._config.get("use_grammar_check")))
        self._grammar_edit.setText(str(self._config.get("grammar_model") or ""))
        quality: str = str(self._config.get("model_quality") or "accurate")
        if quality in ("fast", "balanced", "accurate"):
            idx: int = ["fast", "balanced", "accurate"].index(quality)
            self._quality_combo.setCurrentIndex(idx)
        self._voice_commands_check.setChecked(bool(self._config.get("voice_commands_enabled")))

    def _start_language_discovery(self) -> None:
        if self._language_worker is not None and self._language_worker.isRunning():
            return

        self._language_discovery_succeeded = False
        self._available_languages = []
        self._language_combo.setEnabled(False)
        self._language_status.setText("Checking model language capabilities…")
        self._refresh_button.setText("Checking…")
        self._refresh_button.setEnabled(False)
        worker = _LanguageDiscoveryWorker(
            self._api_edit.text(),
            self._model_edit.text(),
            self._stt_key_edit.text() or None,
        )
        worker.setParent(QCoreApplication.instance())
        worker.languages_ready.connect(self._on_language_discovery_success)
        worker.failed.connect(self._on_language_discovery_failed)
        worker.finished.connect(self._on_language_worker_finished)
        worker.finished.connect(worker.deleteLater)
        self._language_worker = worker
        worker.start()

    def _on_language_worker_finished(self) -> None:
        if self.sender() is not self._language_worker:
            return
        self._language_worker = None
        self._refresh_button.setText("Refresh" if self._language_discovery_succeeded else "Retry")
        self._refresh_button.setEnabled(True)

    def _on_language_discovery_success(self, languages: list[str]) -> None:
        self._language_discovery_succeeded = True
        self._available_languages = list(languages)
        self._refresh_button.setText("Refresh")
        self._language_combo.blockSignals(True)
        self._language_combo.clear()

        if not languages:
            saved_label = next(
                (
                    label
                    for code, label in APP_LANGUAGE_OPTIONS
                    if code == self._saved_transcription_language
                ),
                self._saved_transcription_language,
            )
            self._language_combo.addItem(saved_label, self._saved_transcription_language)
            self._language_combo.setEnabled(False)
            self._language_status.setText(
                "Configured model supports neither English nor Portuguese."
            )
            self._button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            self._language_combo.blockSignals(False)
            return

        for code, label in APP_LANGUAGE_OPTIONS:
            if code in languages:
                self._language_combo.addItem(label, code)

        if self._saved_transcription_language not in languages:
            self._language_combo.addItem(
                f"{self._saved_transcription_language} (not supported by configured model)",
                self._saved_transcription_language,
            )
            model = self._language_combo.model()
            if isinstance(model, QStandardItemModel):
                unavailable = model.item(self._language_combo.count() - 1)
                if unavailable is not None:
                    unavailable.setEnabled(False)
            self._language_combo.setCurrentIndex(
                self._language_combo.findData(self._saved_transcription_language)
            )
            self._language_status.setText("Select a language supported by the configured model.")
            self._button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        else:
            self._language_combo.setCurrentIndex(
                self._language_combo.findData(self._saved_transcription_language)
            )
            self._language_status.clear()
            self._button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

        self._language_combo.setEnabled(True)
        self._language_combo.blockSignals(False)

    def _on_language_discovery_failed(self, message: str) -> None:
        safe_messages = {
            "Unable to read model language capabilities",
            "Invalid model-list response",
            "Configured model was not found",
            "Configured model is not an ASR model",
            "Configured model has no valid language metadata",
        }
        safe_message = (
            message if message in safe_messages else "Unable to read model language capabilities"
        )
        self._language_discovery_succeeded = False
        self._available_languages = []
        self._language_combo.blockSignals(True)
        self._language_combo.clear()
        saved_label = next(
            (
                label
                for code, label in APP_LANGUAGE_OPTIONS
                if code == self._saved_transcription_language
            ),
            self._saved_transcription_language,
        )
        self._language_combo.addItem(saved_label, self._saved_transcription_language)
        self._language_combo.setCurrentIndex(0)
        self._language_combo.setEnabled(False)
        self._language_combo.blockSignals(False)
        self._language_status.setText(safe_message)
        self._refresh_button.setText("Retry")
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

    def _on_language_selection_changed(self) -> None:
        if not self._language_discovery_succeeded:
            return
        selected_language = self._language_combo.currentData()
        is_supported = selected_language in self._available_languages
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(is_supported)
        if is_supported:
            self._language_status.clear()
        else:
            self._language_status.setText("Select a language supported by the configured model.")

    def _apply_config(self) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        updates["stt_api_url"] = self._api_edit.text()
        updates["stt_api_key"] = self._stt_key_edit.text()
        updates["llm_api_url"] = self._llm_api_edit.text()
        updates["llm_api_key"] = self._llm_key_edit.text()
        updates["model_name"] = self._model_edit.text()
        updates["hotkey"] = self._hotkey_edit.text()
        updates["auto_insert"] = self._auto_insert_check.isChecked()
        updates["sample_rate"] = self._sample_spin.value()
        updates["silence_threshold_ms"] = self._silence_spin.value()
        updates["use_grammar_check"] = self._grammar_check.isChecked()
        updates["grammar_model"] = self._grammar_edit.text()
        updates["model_quality"] = self._quality_combo.currentText()
        updates["voice_commands_enabled"] = self._voice_commands_check.isChecked()
        if self._language_discovery_succeeded:
            selected_language = self._language_combo.currentData()
            if selected_language in self._available_languages:
                updates[LANGUAGE_CONFIG_KEY] = selected_language
        return updates

    def _save(self) -> None:
        updates = self._apply_config()
        self._config.save_config(updates)
        logger.info("Settings saved successfully")
        if self._on_saved:
            self._on_saved()

    def _cancel(self) -> None:
        logger.debug("Settings dialog cancelled")

    def _is_recording(self) -> bool:
        """Return whether the hotkey recorder is currently active."""
        return self._is_recording_flag

    def _record_hotkey(self) -> None:
        self._recording_label.setText("Press a key combination...")
        self._recording_label.setVisible(True)
        self._is_recording_flag = True

        # Force layout evaluation so tests can check widget state without show()
        self.updateGeometry()
        self.adjustSize()

        self._record_button.setEnabled(False)

        self._recorder = _HotkeyRecorder()
        self._recorder.finished.connect(self._on_hotkey_captured)
        self._recorder.finished.connect(self._recorder.deleteLater)
        self._recorder.start()

    def _on_hotkey_captured(self, key_str: str) -> None:
        self._hotkey_edit.setText(key_str)
        self._recording_label.setText("")
        self._recording_label.setVisible(False)
        self._is_recording_flag = False
        self._record_button.setEnabled(True)
