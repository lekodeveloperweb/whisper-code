# Task 6: Settings dialog server groups

**Files:**

- Modify: `src/gui/settings_dialog.py`
- Test: `tests/test_settings_dialog.py`

**Interfaces:**

- Consumes: `stt_api_url` / `llm_api_url` / `stt_api_key` / `llm_api_key`
  config keys from task 4.
- Produces: `_stt_key_edit`, `_llm_api_edit`, `_llm_key_edit` widgets;
  `_apply_config()` returns the four keys — consumed by nothing further.

This task repairs the KNOWN TRANSIENT FAILURE declared in index.md
(`test_settings_dialog_populates_from_config` has been failing since
task 4 because the dialog still reads the dead `api_url` key).

- [ ] Step 1: Write the failing tests

In `tests/test_settings_dialog.py`, UPDATE the five pre-existing
assertions that reference the dead key — change every
`["api_url"]` / `("api_url")` occurrence to `"stt_api_url"`:

- `test_settings_dialog_save_writes_config`:
  `assert saved["api_url"] == "http://new-url.com"` →
  `assert saved["stt_api_url"] == "http://new-url.com"`
- `test_settings_dialog_cancel_does_not_save`:
  `assert saved["api_url"] == "http://localhost:8080"` →
  `assert saved["stt_api_url"] == "http://localhost:8080"`
- `test_settings_dialog_apply_config`:
  `assert updates["api_url"] == "http://example.com"` →
  `assert updates["stt_api_url"] == "http://example.com"`
- `test_settings_dialog_save_updates_all_fields`:
  `assert saved["api_url"] == "http://api.example.com"` →
  `assert saved["stt_api_url"] == "http://api.example.com"`
- `test_settings_dialog_reject_button`:
  `assert saved["api_url"] == "http://localhost:8080"` →
  `assert saved["stt_api_url"] == "http://localhost:8080"`

Then APPEND these three tests (the file already imports `json`, `pytest`,
`QDialogButtonBox`, `ConfigManager`, and defines the `qapp` and
`config_manager` fixtures):

```python
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
```

- [ ] Step 2: RED GATE

Run: `uv run pytest tests/test_settings_dialog.py -v`
Expected output: eight tests FAIL — the five updated pre-existing ones with
`KeyError: 'stt_api_url'` / wrong-`api_url`-key `AssertionError`s, plus the
transient `test_settings_dialog_populates_from_config` with `AssertionError`
(`_api_edit.text()` is `""`), and the three new ones with
`AttributeError: 'SettingsDialog' object has no attribute '_stt_key_edit'`
(or `KeyError`). All other tests PASS.
PASTE the output.

- [ ] Step 3: Implement

In `src/gui/settings_dialog.py` apply every block from interfaces.md
§ SettingsDialog changes: new widget creation lines after `self._api_edit`,
the three widgets appended to `_widget_refs` after `self._api_edit,`, and
the full replacements of `_setup_ui`, `_populate_widgets`, and
`_apply_config`.

- [ ] Step 4: GREEN

Run: `uv run pytest tests/test_settings_dialog.py -v`
Expected output: all tests pass (`22 passed` — 19 pre-existing + 3 new),
including `test_settings_dialog_populates_from_config` which was red since
task 4. PASTE the output.
Failure mode this catches: the dialog writing a stale `api_url` key that
config no longer reads (users' saved settings silently ignored), or key
fields echoing secrets on screen (AC-18 masking).

- [ ] Step 5: Lint + type check

Run: `uv run ruff check src/gui/settings_dialog.py && uv run mypy src/gui/settings_dialog.py`
Expected output: no issues found.

- [ ] Step 6: Commit

```bash
git add src/gui/settings_dialog.py tests/test_settings_dialog.py
git commit -m "feat(ui): regroup settings dialog into STT and LLM server sections

Password-echo fields for stt_api_key/llm_api_key; _apply_config now
writes the four split keys (spec AC-18, AC-19)."
```
