# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Whisper-Code** — macOS menu bar app for hands-free voice dictation. Uses a local OpenAI-compatible STT API (oMLX) to transcribe speech, then injects text into the focused app via clipboard + simulated Cmd+V.

## Structure

```
src/
  __main__.py            # Module entry point — calls cli.main() (python -m src.whisper_code)
  cli.py                 # Entry point — wires up WhisperCodeApp, main() function
  core/
    audio_recorder.py    # PyAudio capture → in-memory WAV (no disk writes)
    api_transcriber.py   # POST audio to /v1/audio/transcriptions endpoint
    grammar_checker.py   # POST text to /v1/chat/completions for cleanup
    hotkey_listener.py   # pynput global hotkey: Cmd+Ctrl+T (toggle), Enter (stop)
  gui/
    tray_menu.py         # QSystemTrayIcon with toggle/quit actions
    wave_overlay.py      # Qt.ToolTip ghost HUD with animated waveform bars
  utils/
    config_manager.py    # ~/.config/whisper-code/settings.json + env var overrides (ENV_MAP)
    text_injector.py     # Clipboard backup → Cmd+V paste → restore
tests/
  test_config.py         # ConfigManager smoke tests
```

## Commands

```bash
# Run the app (macOS only, requires PyQt5)
uv run whisper
# or
uv run python -m src.whisper_code

# Run tests
uv run pytest tests/ -v

# Run a single test
uv run pytest tests/test_config.py -v

# Lint with ruff
uv run ruff check .
uv run ruff format --check .

# Type check with mypy
uv run mypy src/

# Run all quality checks (lint + typecheck + test)
make all
```

## Type Checking

All source files are fully type annotated. mypy runs with strict settings:
- `disallow_untyped_defs = true` — all functions must have type hints
- `warn_return_any = true` — no returning `Any` from typed functions
- `check_untyped_defs = true` — check untyped function definitions

Key typing patterns:
- `ConfigManager.get(key)` returns `Any` (can be `None`, `str`, `int`, `bool`)
- `TextInjector.inject_text(text: str | None)` accepts `None` safely
- `AudioRecorder` uses `int` for `sample_rate`, `float` for `rms`
- Callback types use `Callable[[T], None]` pattern (e.g., `TranscribeFinishedCb`)
- `TrayMenu.update_state(is_listening: bool, is_processing: bool) -> None`
- `HotkeyListener` uses `pyqtSignal()` for `triggered` and `confirmed` events

Pre-commit hooks run `ruff` + `mypy` automatically on every commit.

## Architecture

WhisperCodeApp (`src/whisper_code/cli.py:17`) owns the lifecycle. On startup it loads config, instantiates all core components, then calls `setup()` to start the hotkey listener, then starts the PyQt event loop (`app.exec_()`).

Entry points:
- `uv run whisper` → `src.whisper_code.__main__:main` (console script, `pyproject.toml`)
- `uv run python -m src.whisper_code` → `src.whisper_code.__main__.main()` (module entry, calls `cli.main()`)
- `main()` function calls `app = WhisperCodeApp()` then `app.run()`
- `__init__` calls `self.setup()` — only called once (removed from `main()` to prevent double-start)

Hotkey flow: `HotkeyListener` (pynput, background thread) detects Cmd+Ctrl+T → emits `triggered` → `WhisperCodeApp.start_listening()` → `AudioRecorder` starts capturing → user speaks → `AudioRecorder.stop_recording()` → `APITranscriber` POSTs WAV → `finished` signal → `TextInjector` injects into focused app.

Grammar checking is optional: if `use_grammar_check` is true, the transcribed text is POSTed to a separate chat/completions endpoint for cleanup before injection.

Key design decisions:

- Audio stays in-memory (io.BytesIO + wave module). Nothing written to disk.
- HUD uses Qt.ToolTip with 0.0 opacity toggled to 1.0 to bypass macOS focus-switching.
- Text injection uses pyperclip backup + pynput simulated Cmd+V.
- Config lives in `~/.config/whisper-code/settings.json`, merged with defaults then env var overrides on each load.
- Env var priority: env vars > file config > defaults. See `ENV_MAP` in `config_manager.py`.

## Notes

- Requires Python 3.14+ (per pyproject.toml). Managed via `uv`.
- Virtual env in `.venv/`. Lock file at `uv.lock`.
- PRD in `docs/PRD.md`.
- Console script: `whisper` (defined in `pyproject.toml`, points to `src.whisper_code.__main__:main`).
- Config keys: `api_url`, `model_name`, `hotkey`, `auto_insert`, `sample_rate`, `use_grammar_check`, `grammar_model`.
- Env var overrides: `WHISPER_API_URL`, `WHISPER_MODEL_NAME`, `WHISPER_HOTKEY`, `WHISPER_AUTO_INSERT`, `WHISPER_SAMPLE_RATE`, `WHISPER_GRAMMAR_CHECK`, `WHISPER_GRAMMAR_MODEL`.
- Pre-commit hooks: `ruff` (lint) + `mypy` (type check) run automatically on commit.
- Makefile targets: `make lint`, `make typecheck`, `make test`, `make all`.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
