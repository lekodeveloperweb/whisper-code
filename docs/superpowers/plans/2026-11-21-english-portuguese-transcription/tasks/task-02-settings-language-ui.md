# Task 2

Add capability-backed language selection to Settings

**Files:**

- Modify: `src/gui/settings_dialog.py`
- Test: `tests/test_settings_dialog.py`

**Interfaces:**

- Consumes: `fetch_model_languages`, `LanguageDiscoveryError`, and `_LanguageDiscoveryWorker` from `../interfaces.md`; configuration constants from Task 1.
- Produces: Settings combo, initial async discovery, success/error state handlers, and selected-language persistence; Task 3 adds live-field Refresh behavior.

**Task-boundary preconditions for RED:** Task 1 is complete; discovery can return `en`/`pt` or `LanguageDiscoveryError`; Settings has no language combo or capability state.

**Required test-harness setup:** Use the existing `qapp` fixture. Build a test config from `DEFAULT_CONFIG` and override `transcription_language`; patch `PySide6.QtCore.QThread.start` in synchronous UI-state tests so the initial worker does not make a network request. Use `threading.Event` only in the responsiveness test.

- [x] Step 1: Write the failing tests

Add these tests and helpers to `tests/test_settings_dialog.py` (retain the file's existing tests):

```python
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QDialogButtonBox

from src.gui.settings_dialog import SettingsDialog
from src.utils.config_manager import DEFAULT_CONFIG


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
```

- [x] Step 2: RED GATE

Run: `uv run pytest tests/test_settings_dialog.py -q`

Expected RED: imports/setup succeed, then the first new behavior test fails because the language combo/state handlers are absent. Paste the actual output.

- [x] Step 3: Implement

Add the asynchronous worker from `../interfaces.md` and start it on dialog load. Add `_language_combo`, `_language_status`, `_button_box`, `_on_language_discovery_success`, `_on_language_discovery_failed`, `_on_language_selection_changed`, and `_start_language_discovery`. On discovery failure, preserve the saved code and enable unrelated settings save; on a successful unsupported selection, disable OK until a supported code is chosen. `_apply_config()` must emit the selected code after successful discovery without changing existing unrelated fields. If discovery fails, omit `transcription_language` from the update dict so saving unrelated settings leaves the persisted value untouched. Task 3 will wire the control to refresh from edited form values.

- [x] Step 4: GREEN

Run: `uv run pytest tests/test_settings_dialog.py -q`

Expected output: all Settings tests pass. The tests catch wrong labels/codes, accepting an unsupported value, dropping saved language after discovery failure, leaking a key, refreshing stale endpoint/model inputs, or blocking the Qt event loop.

- [x] Step 5: Record completion evidence

Record the exact command and actual output. Do not commit.
