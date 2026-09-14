# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-06-18

### Added

**Core Features**
- Voice dictation flow: activate → listen → transcribe → inject text
- Global hotkey listener (Cmd+Ctrl+T toggle, Enter stop)
- Double-tap Option key hotkey activation
- Speech recognition using local OpenAI-compatible STT API (oMLX)
- Hybrid text injection — tries macOS Accessibility API first, falls back to clipboard+Cmd+V
- In-memory audio capture (BytesIO, no disk writes)

**Audio Processing**
- Silence detection (VAD) with configurable threshold (100-5000ms)
- Speech detection guard (500 RMS threshold)
- Configurable sample rate (default: 16000 Hz)

**UI & Feedback**
- Menu bar status icon with pulsing animation
- HUD wave overlay with 7 animated waveform bars
- Height-based color gradient (green → blue → orange → red)
- Toast notifications for success, error, and warning states
- Confidence percentage display on HUD

**Configuration**
- Settings storage at `~/.config/whisper-code/settings.json`
- Environment variable overrides for all config keys
- Optional grammar checker (POST to `/v1/chat/completions`)

**macOS Integration**
- Permissions handling (Microphone + Accessibility)
- Model download script

### Changed

- Text injection prioritizes Accessibility API to avoid clipboard contamination
- Wave overlay updated with larger bars (60px max height, 10px width) and color gradient

### Technical

| Component | Technology |
|-----------|------------|
| Language | Python 3.14+ |
| GUI | PySide6 (Qt6) |
| Audio I/O | PyAudio |
| Hotkeys | pynput |
| Clipboard | pyperclip |
| STT API | OpenAI-compatible (oMLX) |
| Type Checking | mypy (strict) |
| Linting | ruff |

### Configuration Reference

| Key | Env Var | Default |
|-----|---------|---------|
| `api_url` | `WHISPER_API_URL` | `http://localhost:8080` |
| `model_name` | `WHISPER_MODEL_NAME` | `whisper-large-v3` |
| `hotkey` | `WHISPER_HOTKEY` | `cmd+ctrl+t` |
| `auto_insert` | `WHISPER_AUTO_INSERT` | `true` |
| `sample_rate` | `WHISPER_SAMPLE_RATE` | `16000` |
| `use_grammar_check` | `WHISPER_GRAMMAR_CHECK` | `false` |
| `grammar_model` | `WHISPER_GRAMMAR_MODEL` | `gpt-4` |

### Known Limitations

- Apple Silicon only (M1+)
- English language only
- No continuous dictation mode
- No transcription history

### Requirements

- macOS 12+ (Apple Silicon M1+)
- Python 3.14+
- Microphone access
- Accessibility permissions (for text injection)
