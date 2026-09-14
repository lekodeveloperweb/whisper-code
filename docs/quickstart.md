# Quickstart Guide

Get Whisper-Code running in 2 minutes.

## Prerequisites

- macOS (Apple Silicon recommended)
- Python 3.14+
- A local OpenAI-compatible API running (e.g., oMLX at `http://localhost:8080`)
- `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Installation

```bash
pip install whisper-code
```

Or using uv:

```bash
uv sync
```

## First Run

```bash
uv run whisper
```

Or:

```bash
uv run python -m src.whisper_code
```

A green circle icon appears in your macOS menu bar.

## Start Dictating

1. Press **`Cmd + Ctrl + T`** — the "Listening..." HUD fades in
2. Speak naturally into your microphone
3. Press **ENTER** to stop and send
4. Transcribed text appears at your cursor

## Configuration

Settings are stored in `~/.config/whisper-code/settings.json`. Edit it to match your API:

```json
{
    "api_url": "http://localhost:8080",
    "model_name": "whisper-large-v3",
    "hotkey": "Cmd+Ctrl+T",
    "auto_insert": true,
    "sample_rate": 16000,
    "use_grammar_check": true,
    "grammar_model": "gemma4-e4b-8b"
}
```

## Next Steps

- Read the [Installation Guide](installation.md) for detailed setup
- Check [Configuration](configuration.md) for environment variable overrides
- See [Usage](usage.md) for hotkey and HUD details
