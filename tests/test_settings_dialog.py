from __future__ import annotations

import json
from threading import Event
from unittest.mock import MagicMock, patch

import pytest
import requests
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialogButtonBox

from src.gui.settings_dialog import SettingsDialog, _LanguageDiscoveryWorker
from src.utils.config_manager import DEFAULT_CONFIG, ConfigManager

SAMPLE_RATE = 16000
SAMPLE_RATE_ALT = 22050
SAMPLE_RATE_HIGH = 32000
QUALITY_FAST = 0
QUALITY_BALANCED = 1
QUALITY_ACCURATE = 2


@pytest.fixture
def config_manager(tmp_path):
    config = ConfigManager()
    config.config = DEFAULT_CONFIG.copy()
    config.config_file = tmp_path / "settings.json"
    config.save_config(config.config)
    return config


def test_settings_dialog_initializes(qapp, config_manager):
    from src.gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(config_manager)
    assert dialog is not None
    assert dialog.windowTitle() == "Settings"


def test_settings_dialog_populates_from_config(qapp, config_manager):
    from src.gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(config_manager)
    dialog._populate_widgets()

    assert dialog._api_edit.text() == "http://localhost:8080"
    assert dialog._model_edit.text() == "Systran/faster-whisper-small"
    assert dialog._hotkey_edit.text() == "Cmd+Ctrl+T"
    assert dialog._auto_insert_check.isChecked() is True
    assert dialog._sample_spin.value() == SAMPLE_RATE
    assert dialog._grammar_check.isChecked() is True
    assert dialog._grammar_edit.text() == "gemma4-e4b-8b"


def test_settings_dialog_save_writes_config(qapp, config_manager):
    from src.gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(config_manager)
    dialog._api_edit.setText("http://new-url.com")
    dialog._model_edit.setText("new-model")
    dialog._save()

    saved = json.loads(config_manager.config_file.read_text())
    assert saved["stt_api_url"] == "http://new-url.com"
    assert saved["model_name"] == "new-model"


def test_settings_dialog_cancel_does_not_save(qapp, config_manager):
    from src.gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(config_manager)
    dialog._api_edit.setText("http://new-url.com")
    dialog._cancel()

    saved = json.loads(config_manager.config_file.read_text())
    assert saved["stt_api_url"] == "http://localhost:8080"


def test_settings_dialog_apply_config(qapp, config_manager):
    from src.gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(config_manager)
    dialog._api_edit.setText("http://example.com")
    dialog._model_edit.setText("test-model")
    dialog._auto_insert_check.setChecked(False)
    dialog._sample_spin.setValue(22050)
    dialog._grammar_check.setChecked(False)
    dialog._grammar_edit.setText("custom-model")

    updates = dialog._apply_config()

    assert updates["stt_api_url"] == "http://example.com"
    assert updates["model_name"] == "test-model"
    assert updates["auto_insert"] is False
    assert updates["sample_rate"] == SAMPLE_RATE_ALT
    assert updates["use_grammar_check"] is False
    assert updates["grammar_model"] == "custom-model"


def test_hotkey_recorder_formats_combo():
    from pynput import keyboard

    from src.gui.settings_dialog import _format_hotkey

    cmd_key = keyboard.Key.cmd
    ctrl_key = keyboard.Key.ctrl
    char_key = type("MockKey", (), {"char": "X"})()

    keys = [cmd_key, ctrl_key, char_key]
    result = _format_hotkey(keys)
    assert result == "Cmd+Ctrl+X"


def test_hotkey_recorder_formats_single_key():

    from src.gui.settings_dialog import _format_hotkey

    key = type("MockKey", (), {"char": "Q"})()
    result = _format_hotkey([key])
    assert result == "Q"


def test_hotkey_recorder_formats_cmd_only():
    from pynput import keyboard

    from src.gui.settings_dialog import _format_hotkey

    keys = [keyboard.Key.cmd, type("MockKey", (), {"char": "Z"})()]
    result = _format_hotkey(keys)
    assert result == "Cmd+Z"


def test_settings_dialog_save_updates_all_fields(qapp, config_manager):
    from src.gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(config_manager)
    dialog._api_edit.setText("http://api.example.com")
    dialog._model_edit.setText("whisper-tiny")
    dialog._hotkey_edit.setText("Alt+Space")
    dialog._auto_insert_check.setChecked(False)
    dialog._sample_spin.setValue(32000)
    dialog._grammar_check.setChecked(False)
    dialog._grammar_edit.setText("llama3-8b")
    dialog._save()

    saved = json.loads(config_manager.config_file.read_text())
    assert saved["stt_api_url"] == "http://api.example.com"
    assert saved["model_name"] == "whisper-tiny"
    assert saved["hotkey"] == "Alt+Space"
    assert saved["auto_insert"] is False
    assert saved["sample_rate"] == SAMPLE_RATE_HIGH
    assert saved["use_grammar_check"] is False
    assert saved["grammar_model"] == "llama3-8b"


def test_settings_dialog_reject_button(qapp, config_manager):
    from src.gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(config_manager)
    dialog._api_edit.setText("http://changed.com")

    button = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.Cancel)
    button.click()

    saved = json.loads(config_manager.config_file.read_text())
    assert saved["stt_api_url"] == "http://localhost:8080"


def test_hotkey_recorder_init(qapp):
    import threading

    from src.gui.settings_dialog import _HotkeyRecorder

    recorder = _HotkeyRecorder()
    assert isinstance(recorder._stop_event, threading.Event)


def test_hotkey_recorder_finished_signal(qapp):

    from src.gui.settings_dialog import _HotkeyRecorder

    recorder = _HotkeyRecorder()
    results = []
    recorder.finished.connect(results.append)
    recorder.finished.emit("test key")
    assert results == ["test key"]


def test_format_hotkey_with_cmd_ctrl(qapp):
    from pynput import keyboard

    from src.gui.settings_dialog import _format_hotkey

    cmd_key = keyboard.Key.cmd
    ctrl_key = keyboard.Key.ctrl
    char_key = type("MockKey", (), {"char": "X"})()

    keys = [cmd_key, ctrl_key, char_key]
    result = _format_hotkey(keys)
    assert result == "Cmd+Ctrl+X"


def test_settings_dialog_record_hotkey_creates_recorder(qapp, config_manager):
    from src.gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(config_manager)
    dialog._record_button.clicked.emit()

    recorder = dialog._recorder
    assert recorder is not None

    recorder._stop_event.set()
    recorder.wait(5000)


def test_settings_dialog_record_hotkey_shows_label(qapp, config_manager):
    from src.gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(config_manager)
    # Directly call _record_hotkey() since clicked.emit() doesn't trigger slots in pytest.
    dialog._record_hotkey()

    # The recording state should be active and show the message immediately.
    assert dialog._is_recording()
    assert dialog._recording_label.text() == "Press a key combination..."

    # Unblock the recorder thread so it finishes cleanly.
    if dialog._recorder is not None:
        dialog._recorder._stop_event.set()
        dialog._recorder.wait(5000)


def test_settings_dialog_populates_quality_from_config(qapp, config_manager):
    """Quality selector defaults to 'accurate'."""
    from PySide6.QtWidgets import QComboBox

    from src.gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(config_manager)
    assert hasattr(dialog, "_quality_combo")
    assert isinstance(dialog._quality_combo, QComboBox)
    # Default should be "accurate" (index 2)
    assert dialog._quality_combo.currentIndex() == QUALITY_ACCURATE
    assert dialog._quality_combo.currentText() == "accurate"


def test_settings_dialog_save_quality_writes_config(qapp, config_manager):
    """Changing quality selector writes to config."""
    import json

    from src.gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(config_manager)
    dialog._quality_combo.setCurrentIndex(QUALITY_FAST)  # "fast"
    dialog._save()

    saved = json.loads(config_manager.config_file.read_text())
    assert saved["model_quality"] == "fast"


def test_settings_dialog_quality_balanced(qapp, config_manager):
    """Quality selector can be set to 'balanced'."""
    from src.gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(config_manager)
    dialog._quality_combo.setCurrentIndex(QUALITY_BALANCED)  # "balanced"
    dialog._save()

    saved_quality = dialog._config.get("model_quality")
    assert saved_quality == "balanced"


def test_settings_dialog_recorder_thread_finishes_promptly(qapp, config_manager):
    """Regression: _HotkeyRecorder must not block past listener join().

    The pynput stub's join() used to block forever, leaving this QThread
    running at Qt module shutdown — qFatal() abort and a native macOS
    crash-report window on every full test run.
    """
    from src.gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(config_manager)
    dialog._record_hotkey()

    assert dialog._recorder is not None
    assert dialog._recorder.wait(2000), "recorder thread did not finish within 2s"


def test_dialog_populates_split_server_fields(qapp, config_manager):
    """AC-18: STT URL/key populate the right fields; key field is masked."""
    from PySide6.QtWidgets import QLineEdit

    from src.gui.settings_dialog import SettingsDialog

    config_manager.config.update({"stt_api_url": "http://a:1", "stt_api_key": "sk-1"})
    dialog = SettingsDialog(config_manager)
    dialog._populate_widgets()

    assert dialog._api_edit.text() == "http://a:1"
    assert dialog._stt_key_edit.text() == "sk-1"
    assert dialog._stt_key_edit.echoMode() == QLineEdit.EchoMode.Password
    assert dialog._llm_key_edit.echoMode() == QLineEdit.EchoMode.Password


def test_dialog_apply_config_contains_four_keys(qapp, config_manager):
    """AC-18: the update dict carries the four server/auth keys."""
    from src.gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(config_manager)
    updates = dialog._apply_config()

    for key in ("stt_api_url", "llm_api_url", "stt_api_key", "llm_api_key"):
        assert key in updates, key


def test_dialog_save_writes_llm_url_to_disk(qapp, config_manager):
    """AC-19: saving the dialog persists llm_api_url to settings.json."""
    from src.gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(config_manager)
    dialog._llm_api_edit.setText("http://x:9")
    dialog._save()

    saved = json.loads(config_manager.config_file.read_text())
    assert saved["llm_api_url"] == "http://x:9"


@pytest.fixture(autouse=True)
def prevent_language_discovery_network(monkeypatch, request):
    from src.gui import settings_dialog

    worker_type = getattr(settings_dialog, "_LanguageDiscoveryWorker", None)
    if (
        worker_type is not None
        and request.node.name != "test_settings_event_loop_runs_while_get_is_blocked"
    ):
        monkeypatch.setattr(worker_type, "start", lambda self: self.finished.emit())


class FakeConfig:
    def __init__(self, **overrides):
        self.values = {**DEFAULT_CONFIG, **overrides}

    def get(self, key):
        return self.values.get(key)


def make_dialog(qapp, saved_language="pt"):
    from src.gui.settings_dialog import SettingsDialog

    config = FakeConfig(transcription_language=saved_language)
    with patch("PySide6.QtCore.QThread.start"):
        return SettingsDialog(config)


def ok_button(dialog):
    return dialog._button_box.button(QDialogButtonBox.StandardButton.Ok)


def test_language_combo_has_only_english_and_portuguese(qapp):
    dialog = make_dialog(qapp)
    dialog._on_language_discovery_success(["en", "pt"])
    combo = dialog._language_combo
    assert [(combo.itemData(i), combo.itemText(i)) for i in range(combo.count())] == [
        ("en", "English"),
        ("pt", "Portuguese"),
    ]
    assert combo.currentData() == "pt"


def test_unsupported_saved_language_requires_valid_choice(qapp):
    dialog = make_dialog(qapp, saved_language="pt")
    dialog._on_language_discovery_success(["en"])
    combo = dialog._language_combo
    unavailable = next(i for i in range(combo.count()) if combo.itemData(i) == "pt")
    assert not combo.model().item(unavailable).isEnabled()
    assert not ok_button(dialog).isEnabled()
    combo.setCurrentIndex(0)
    dialog._on_language_selection_changed()
    assert combo.currentData() == "en"
    assert ok_button(dialog).isEnabled()


def test_model_without_app_languages_blocks_accept(qapp):
    dialog = make_dialog(qapp, saved_language="en")
    dialog._on_language_discovery_success([])
    assert not ok_button(dialog).isEnabled()
    assert "neither English nor Portuguese" in dialog._language_status.text()


@pytest.mark.parametrize(
    "message",
    [
        "Configured model is not an ASR model",
        "Configured model has no valid language metadata",
        "Configured model was not found",
        "Unable to read model language capabilities",
    ],
)
def test_discovery_failure_preserves_language_and_allows_other_save(qapp, message):
    dialog = make_dialog(qapp, saved_language="pt")
    dialog._on_language_discovery_failed(message)
    assert dialog._language_combo.currentData() == "pt"
    assert not dialog._language_combo.isEnabled()
    assert dialog._language_status.text()
    assert ok_button(dialog).isEnabled()
    dialog._auto_insert_check.setChecked(False)
    values = dialog._apply_config()
    assert "transcription_language" not in values
    assert values["auto_insert"] is False


def test_settings_acceptance_includes_selected_language(qapp):
    dialog = make_dialog(qapp)
    dialog._on_language_discovery_success(["en", "pt"])
    dialog._language_combo.setCurrentIndex(1)
    assert dialog._apply_config()["transcription_language"] == "pt"


def test_refresh_uses_current_url_key_and_model(qapp):
    dialog = make_dialog(qapp)
    dialog._api_edit.setText("http://changed-stt/")
    dialog._stt_key_edit.setText("changed-key")
    dialog._model_edit.setText("Systran/faster-whisper-small")
    worker = MagicMock()
    with patch("src.gui.settings_dialog._LanguageDiscoveryWorker", return_value=worker) as factory:
        dialog._refresh_button.click()
        assert not dialog._refresh_button.isEnabled()
        dialog._start_language_discovery()
    factory.assert_called_once_with(
        "http://changed-stt/",
        "Systran/faster-whisper-small",
        "changed-key",
    )
    worker.start.assert_called_once_with()


def test_http_401_with_api_key_is_not_exposed_in_error_text(qapp):
    response = MagicMock()
    response.raise_for_status.side_effect = requests.HTTPError("401")
    errors = []
    worker = _LanguageDiscoveryWorker("http://stt", "model", "secret-test-key")
    worker.failed.connect(errors.append)
    with patch("src.core.api_language_discovery.requests.get", return_value=response) as get:
        worker.run()
    assert get.call_args.kwargs["headers"] == {"Authorization": "Bearer secret-test-key"}
    dialog = make_dialog(qapp)
    dialog._on_language_discovery_failed(errors[0])
    assert "secret-test-key" not in dialog._language_status.text()


def test_settings_event_loop_runs_while_get_is_blocked(qapp):
    started = Event()
    release = Event()
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"data": []}

    def blocked_get(*args, **kwargs):
        started.set()
        release.wait(2)
        return response

    dialog = None
    try:
        with patch("src.core.api_language_discovery.requests.get", side_effect=blocked_get):
            dialog = SettingsDialog(FakeConfig(transcription_language="en"))
            assert started.wait(1)
            processed = []
            QTimer.singleShot(0, lambda: processed.append(True))
            qapp.processEvents()
            assert processed == [True]
    finally:
        release.set()
        if dialog is not None:
            worker = dialog._language_worker
            if worker is not None:
                worker.wait(1000)
            qapp.processEvents()
            dialog.close()
