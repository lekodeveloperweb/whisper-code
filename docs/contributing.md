# Contributing Guide

Help improve Whisper-Code!

## Setup

```bash
git clone <repository-url>
cd whisper-code
uv sync
```

## Development Workflow

### Lint

```bash
uv run ruff check .
```

### Type Check

```bash
uv run mypy src/
```

### Run All Checks

```bash
make all
```

This runs lint, typecheck, and tests in one command.

### Run Tests

```bash
uv run pytest tests/ -v
```

Or a single test:

```bash
uv run pytest tests/test_config.py -v
```

## Project Structure

```
src/
  __main__.py            # Module entry point
  cli.py                 # Entry point — wires up WhisperCodeApp
  core/
    audio_recorder.py    # PyAudio capture → in-memory WAV
    api_transcriber.py   # POST audio to STT API
    grammar_checker.py   # POST text for grammar cleanup
    hotkey_listener.py   # pynput global hotkey
  gui/
    tray_menu.py         # QSystemTrayIcon tray menu
    wave_overlay.py      # Qt.ToolTip ghost HUD
  utils/
    config_manager.py    # settings.json + env var overrides
    text_injector.py     # Clipboard backup + Cmd+V paste
tests/
  test_config.py         # ConfigManager smoke tests
```

## Making Changes

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Run `make all` to ensure everything passes
4. Commit with a descriptive message
5. Push and open a Pull Request

## Commit Messages

Follow conventional commits:

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation changes
- `refactor:` code refactoring
- `test:` test additions/changes
- `chore:` maintenance tasks

## PR Checklist

- [ ] `make all` passes
- [ ] Tests updated if behavior changed
- [ ] Documentation updated if needed
- [ ] No debug prints or TODOs left in code
- [ ] Descriptive PR title and description

## Reporting Issues

When filing a bug report, include:

- macOS version
- Python version
- Steps to reproduce
- Expected vs. actual behavior
- Any relevant logs from the menu bar tray

## Adding Dependencies

1. Add to `pyproject.toml` in the appropriate section
2. Run `uv sync` to update the lockfile
3. Run `make all` to verify nothing broke

## Release Process

```bash
bash scripts/build-mac.sh --patch    # or --minor or --major
```

This bumps the version, creates a git tag, and updates `CHANGELOG.md`.
