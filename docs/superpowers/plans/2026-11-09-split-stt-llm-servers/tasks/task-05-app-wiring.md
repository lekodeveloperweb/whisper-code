# Task 5: App wiring + hot-reload + startup log

**Files:**

- Modify: `src/whisper_code/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**

- Consumes: `APITranscriber(api_url, model_name, api_key)` from task 2;
  `GrammarChecker(api_url, model_name, api_key)` from task 3;
  `ConfigManager.resolved_llm_url()` and `stt_api_url` key from task 4.
- Produces: renamed `_apply_stt_url()`, new `_optional_str()` — consumed by
  task 6 tests indirectly (dialog → `_apply_settings`).

- [x] Step 1: Write the failing tests

In `tests/test_cli.py`, first UPDATE the `mock_config` fixture (around
line 82): change the dict key `"api_url": "http://localhost:8080",` to
`"stt_api_url": "http://localhost:8080",` and add this line right after
`cm.get.side_effect = {...}.get`:

```python
        cm.resolved_llm_url.return_value = "http://localhost:8080"
```

(The `_make_grammar_checker` wiring now calls `config.resolved_llm_url()`;
the fixture's mock must answer it with a string.)

Then APPEND these four tests to the end of `tests/test_cli.py` (the file
already imports `MagicMock`, `patch`, `pytest`, and defines the
`mock_pyaudio`, `mock_keyboard`, `mock_components`, `mock_config`, and
`qapp` fixtures):

```python
def test_init_wires_stt_key_and_llm_fallback(qapp, mock_config):
    """AC-15: STT key reaches the transcriber; unset LLM URL falls back
    to the STT server; keys stay independent."""
    import logging

    from src.whisper_code.cli import WhisperCodeApp

    values = {
        "stt_api_url": "http://a:1",
        "stt_api_key": "k1",
        "llm_api_url": None,
        "llm_api_key": None,
        "model_name": "whisper-large-v3",
        "model_quality": "accurate",
        "grammar_model": "gemma4-e4b-8b",
        "use_grammar_check": True,
        "sample_rate": 16000,
    }
    mock_config.get.side_effect = values.get
    mock_config.resolved_llm_url.side_effect = lambda: str(
        values["llm_api_url"] or values["stt_api_url"]
    )

    with (
        patch("src.whisper_code.cli.AudioRecorder"),
        patch("src.whisper_code.cli.WaveOverlay"),
        patch("src.whisper_code.cli.TrayMenu"),
        patch("src.whisper_code.cli.HotkeyListener"),
        patch("src.whisper_code.cli.TextInjector"),
        patch("src.whisper_code.cli.ToastNotifier"),
    ):
        app = WhisperCodeApp(app=qapp)  # APITranscriber / GrammarChecker are REAL

    assert app.transcriber.api_key == "k1"
    assert app.grammar_checker.api_endpoint == "http://a:1/v1/chat/completions"
    assert app.grammar_checker.api_key is None
    logging.getLogger("whisper").handlers.clear()


def test_apply_settings_hot_reloads_llm_url(qapp, mock_components, mock_config):
    """AC-16: a saved llm_api_url propagates to the grammar endpoint."""
    mock_config.resolved_llm_url.return_value = "http://new:2"
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.grammar_checker.api_endpoint = "http://old:1/v1/chat/completions"

    app._apply_settings()

    assert app.grammar_checker.api_endpoint == "http://new:2/v1/chat/completions"


def test_apply_settings_hot_reloads_api_keys(qapp, mock_components, mock_config):
    """AC-17: both keys flow to their own component on _apply_settings."""
    values = {
        "stt_api_url": "http://a:1",
        "stt_api_key": "k9",
        "llm_api_key": "k8",
        "model_name": "whisper-large-v3",
        "model_quality": "accurate",
        "grammar_model": "gemma4-e4b-8b",
        "use_grammar_check": True,
        "sample_rate": 16000,
        "hotkey": "Cmd+Ctrl+T",
    }
    mock_config.get.side_effect = values.get
    mock_config.resolved_llm_url.return_value = "http://a:1"
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.transcriber.api_key = "old-stt"
    app.grammar_checker.api_key = "old-llm"

    app._apply_settings()

    assert app.transcriber.api_key == "k9"
    assert app.grammar_checker.api_key == "k8"


def test_log_startup_never_logs_api_keys(qapp, mock_components, mock_config, caplog):
    """AC-20: startup log shows both URLs but never the secret values."""
    import logging

    from src.whisper_code.cli import WhisperCodeApp

    values = {
        "stt_api_url": "http://a:1",
        "stt_api_key": "secret-stt",
        "llm_api_key": "secret-llm",
        "model_name": "whisper-large-v3",
        "model_quality": "accurate",
        "grammar_model": "gemma4-e4b-8b",
        "use_grammar_check": True,
        "sample_rate": 16000,
        "hotkey": "Cmd+Ctrl+T",
    }
    mock_config.get.side_effect = values.get
    mock_config.resolved_llm_url.return_value = "http://b:2"

    caplog.set_level(logging.DEBUG, logger="whisper")
    WhisperCodeApp(app=qapp)  # __init__ -> setup() -> _log_startup()

    records = "\n".join(r.getMessage() for r in caplog.records)
    assert "http://a:1" in records
    assert "http://b:2" in records
    assert "secret-stt" not in records
    assert "secret-llm" not in records
```

- [x] Step 2: RED GATE

Run: `uv run pytest tests/test_cli.py -v`
Expected output: exactly the four new tests FAIL.
`test_init_wires_stt_key_and_llm_fallback` with
`AttributeError: 'APITranscriber' object has no attribute 'api_key'`; the
two `_apply_settings` tests and `test_log_startup_never_logs_api_keys` with
`AssertionError` (old code reads the dead `api_url` key and never touches
`.api_key`). All 43 pre-existing tests PASS (the fixture change is inert
against the old wiring because `config.get("api_url")` on the mock now
returns `None` and the old code falls back to `http://localhost:8080`).
PASTE the output.

- [x] Step 3: Implement

In `src/whisper_code/cli.py` apply the blocks from interfaces.md
§ WhisperCodeApp changes:

1. Change the config import line to
   `from src.utils.config_manager import STT_URL_DEFAULT, ConfigManager`.
2. Add the `_optional_str` helper method (place it right before
   `_make_transcriber`).
3. Replace `_make_transcriber` and `_make_grammar_checker` with the
   interfaces.md blocks.
4. Replace `_log_startup` with the interfaces.md block.
5. Replace `_apply_api_url` with `_apply_stt_url` (interfaces.md block) and
   update its call site in `_apply_settings`:
   `self._apply_api_url()` → `self._apply_stt_url()`.
6. Replace `_apply_grammar_config` with the interfaces.md block — it keeps
   the grammar-model hot-reload lines inside the new body.

- [x] Step 4: GREEN

Run: `uv run pytest tests/test_cli.py -v`
Expected output: all tests pass (`47 passed` — 43 pre-existing + 4 new).
PASTE the output.
Failure mode this catches: key leaking to the wrong component (AC-15
independence), hot-reload missing the new URL (AC-16) or keys (AC-17), and
secrets appearing in logs (AC-20).

- [x] Step 5: Lint + type check

Run: `uv run ruff check src/whisper_code/cli.py && uv run mypy src/whisper_code/cli.py`
Expected output: no issues found.

- [x] Step 6: Commit

```bash
git add src/whisper_code/cli.py tests/test_cli.py
git commit -m "feat(app): wire STT/LLM servers through app and hot-reload

_make_*/_apply_* read stt_api_url + per-server keys; LLM endpoint
resolves via ConfigManager.resolved_llm_url(); startup log shows both
URLs, never the keys (spec AC-15, AC-16, AC-17, AC-20)."
```
