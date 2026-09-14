# Architecture Guide

How Whisper-Code works under the hood.

## Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    WhisperCodeApp                           │
│  (lifecycle owner, wires all components together)           │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ HotkeyListener │    │  AudioRecorder │    │   TrayMenu    │
│  (pynput)     │    │  (PyAudio)     │    │  (PySide6)    │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │
        │ triggered           │ stop_recording
        ▼                     ▼
┌───────────────┐    ┌───────────────┐
│  start_listening│   │ APITranscriber │
│  (app method)  │    │  (requests)    │
└───────────────┘    └───────────────┘
                              │
                              │ finished
                              ▼
                    ┌───────────────┐
                    │ TextInjector  │
                    │ (pyperclip +  │
                    │  pynput)      │
                    └───────────────┘
                              │
                    (optional)
                              │
                    ┌───────────────┐
                    │GrammarChecker │
                    │ (chat/complet.)│
                    └───────────────┘
```

## Data Flow

1. **Hotkey Listener** (pynput, background thread) detects `Cmd+Ctrl+T`
2. Emits `triggered` signal → `WhisperCodeApp.start_listening()`
3. **AudioRecorder** starts capturing via PyAudio → in-memory WAV buffer
4. User speaks → presses `Enter` → `stop_recording()`
5. **APITranscriber** POSTs WAV to `/v1/audio/transcriptions`
6. On `finished` signal → optional **GrammarChecker** POSTs to `/v1/chat/completions`
7. **TextInjector** injects text via clipboard + simulated `Cmd+V`

## Key Design Decisions

### In-Memory Audio
Audio stays in `io.BytesIO` — nothing written to disk. Chunks are processed and discarded.

### Ghost HUD
Uses Qt.ToolTip with 0.0 opacity toggled to 1.0 to bypass macOS focus-switching. Your cursor never leaves your editor.

### Text Injection
- Primary: macOS Accessibility API for direct cursor placement
- Fallback: pyperclip backup + pynput simulated `Cmd+V`
- Original clipboard is preserved and restored

### Config Loading
Config is reloaded on each access, merging defaults → file config → env vars. Priority: env vars > file config > defaults.

## Build Instructions

### Standalone .app

```bash
bash scripts/build-mac.sh --patch --build
```

Creates `dist/Whisper-Code.app`. Uses PyInstaller with hidden imports for:
- `mlx`, `mlx.nn`, `mlx.utils`
- `pyaudio`, `pynput`, `pyperclip`
- `PySide6`

### Code Signing (Optional)

```bash
codesign --deep --sign "Developer ID Application: Your Name (TEAM ID)" --force dist/Whisper-Code
xcrun notary submit dist/Whisper-Code.dmg --wait
xcrun stapler staple dist/Whisper-Code.dmg
```

## Module Structure

```
src/
  __main__.py            # Entry point — calls cli.main()
  cli.py                 # Wires up WhisperCodeApp, main() function
  core/
    audio_recorder.py    # PyAudio capture → in-memory WAV
    api_transcriber.py   # POST audio to /v1/audio/transcriptions
    grammar_checker.py   # POST text to /v1/chat/completions
    hotkey_listener.py   # pynput global hotkey
  gui/
    tray_menu.py         # QSystemTrayIcon with toggle/quit actions
    wave_overlay.py      # Qt.ToolTip ghost HUD
  utils/
    config_manager.py    # ~/.config/whisper-code/settings.json
    text_injector.py     # Clipboard backup → Cmd+V paste → restore
```
