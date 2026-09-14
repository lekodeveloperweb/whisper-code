from __future__ import annotations

import json

import pytest
from PySide6.QtWidgets import QDialogButtonBox

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
    assert dialog._model_edit.text() == "whisper-large-v3"
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
    assert saved["api_url"] == "http://new-url.com"
    assert saved["model_name"] == "new-model"


def test_settings_dialog_cancel_does_not_save(qapp, config_manager):
    from src.gui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(config_manager)
    dialog._api_edit.setText("http://new-url.com")
    dialog._cancel()

    saved = json.loads(config_manager.config_file.read_text())
    assert saved["api_url"] == "http://localhost:8080"


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

    assert updates["api_url"] == "http://example.com"
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
    assert saved["api_url"] == "http://api.example.com"
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
    assert saved["api_url"] == "http://localhost:8080"


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
