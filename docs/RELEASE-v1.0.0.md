# Whisper-Code v1.0.0 Release Notes

**Release Date:** 2026-06-18  
**Version:** 1.0.0  
**Build:** Initial release

---

## Overview

Whisper-Code is a macOS menu bar application for hands-free voice dictation. It uses a local OpenAI-compatible STT API (oMLX) to transcribe speech and injects text into the focused application via clipboard + simulated Cmd+V.

---

## What's New

### Core Features

- **Voice Dictation Flow** — Activate → Listen → Transcribe → Inject
- **Global Hotkey** — Cmd+Ctrl+T to toggle, Enter to stop
- **Local STT** — Uses oMLX (OpenAI-compatible API) for speech recognition
- **Text Injection** — Tries macOS Accessibility API first, falls back to clipboard+Cmd+V
- **Visual HUD** — Waveform overlay with animated bars showing listening state

### Audio Processing

- **In-Memory Audio** — No disk writes, uses BytesIO
- **Silence Detection (VAD)** — Configurable threshold (100-5000ms) with 500 RMS speech guard
- **Waveform Visualization** — 7 animated bars with height-based color gradient (green → blue → orange → red)

### UI & UX

- **Menu Bar Icon** — Status indicator with pulsing animation
- **HUD Overlay** — Translucent tooltip with waveform bars
- **Toast Notifications** — Success, error, and warning messages
- **Settings Storage** — JSON config at `~/.config/whisper-code/settings.json` with env var overrides

### Grammar Checking (Optional)

- POSTs transcribed text to `/v1/chat/completions` for cleanup
- Configurable via `use_grammar_check` setting

---

## Technical Details

| Component | Technology |
|-----------|------------|
| Language | Python 3.14+ |
| GUI | PySide6 (Qt6) |
| Audio I/O | PyAudio |
| Hotkeys | pynput |
| Clipboard | pyperclip |
| STT API | OpenAI-compatible (oMLX) |

---

## Requirements

- macOS 12+ (Apple Silicon M1+)
- Python 3.14+
- Microphone access
- Accessibility permissions (for text injection)

---

## Installation

```bash
# Clone and install
git clone <repo>
cd whisper-code
uv sync

# Run
uv run whisper
```

---

## Configuration

Settings file: `~/.config/whisper-code/settings.json`

| Key | Env Var | Default |
|-----|---------|---------|
| `api_url` | `WHISPER_API_URL` | `http://localhost:8080` |
| `model_name` | `WHISPER_MODEL_NAME` | `whisper-large-v3` |
| `hotkey` | `WHISPER_HOTKEY` | `cmd+ctrl+t` |
| `auto_insert` | `WHISPER_AUTO_INSERT` | `true` |
| `sample_rate` | `WHISPER_SAMPLE_RATE` | `16000` |
| `use_grammar_check` | `WHISPER_GRAMMAR_CHECK` | `false` |
| `grammar_model` | `WHISPER_GRAMMAR_MODEL` | `gpt-4` |

---

## Known Limitations

- Apple Silicon only (M1+)
- English language only
- No continuous dictation
- No transcription history

---

## Credits

Built with love for hands-free productivity.
