# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-11-09

### Added

- **Split STT and LLM server configuration.** The transcription path and the
  grammar-check path can now target different OpenAI-compatible servers via
  four config keys: `stt_api_url`, `stt_api_key`, `llm_api_url`,
  `llm_api_key`, each overridable by `WHISPER_STT_API_URL`,
  `WHISPER_STT_API_KEY`, `WHISPER_LLM_API_URL`, `WHISPER_LLM_API_KEY`.
  `llm_api_url` unset or empty falls back to `stt_api_url`
  (`ConfigManager.resolved_llm_url()`), so single-server setups need no new
  config.
- **Per-server Bearer auth.** When a key is set, both the transcription and
  grammar requests send `Authorization: Bearer <key>`. An empty or absent key
  sends no `Authorization` header, keeping local no-auth servers working.
- **Settings dialog regrouped** into "STT Server" and "LLM Server" sections
  with password-echoed key fields, so secrets are no longer echoed on screen.

### Changed

- **BREAKING:** `api_url` and `WHISPER_API_URL` were removed with no alias.
  Rename `api_url` to `stt_api_url` in `~/.config/whisper-code/settings.json`
  (or set `WHISPER_STT_API_URL`); the app otherwise falls back to
  `http://localhost:8080`.
- The startup log line now shows both server URLs and never the key values.
- Hot-reload on settings save propagates URL and key changes to both the
  transcriber and the grammar checker without a restart.

## [1.0.1] - 2026-11-09

### Fixed

- **Clicking the menu bar icon aborted the process** with
  `NSInternalInconsistencyException: Invalid message sent to event "NSEvent:
  type=SysDefined ..."`. The tray menu was attached with
  `QSystemTrayIcon.setContextMenu()`, which makes Qt's cocoa plugin
  (`QStatusItemDelegate` in `libqcocoa`) observe the status-item menu's
  begin-tracking notification and read `clickCount` off `[NSApp currentEvent]`.
  `-[NSEvent clickCount]` is only valid for mouse events, so when a
  system-defined event was current — an Fn/Globe or media-key event, which
  pynput's global keyboard tap shares the Cocoa event stream with — AppKit
  raised through Qt's observer and `libc++abi` called `abort()`. `TrayMenu` now
  owns the menu and pops it from the `activated` signal, deferred to the next
  event-loop tick, so Qt never installs that observer and no foreign event is
  current while the menu starts tracking.

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
