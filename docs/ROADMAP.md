# Roadmap

Timeline and milestones for Whisper-Code development.

---

## V0.1.0 (MVP) — Current

**Goal:** Core dictation flow that works reliably on macOS.

### Implemented

- [x] Menu bar tray icon with microphone icon (programmatically drawn)
- [x] Ghost HUD with animated waveform bars (Qt.ToolTip, opacity toggle)
- [x] Tray menu toggle action (start/stop dictation)
- [x] Global hotkey: `Cmd+Ctrl+T` to start, `Enter` to stop
- [x] Speech recognition via local OpenAI-compatible API (oMLX)
- [x] In-memory audio capture (PyAudio → BytesIO WAV, no disk writes)
- [x] Clipboard-based text injection (pyperclip + simulated Cmd+V)
- [x] Settings persistence (`~/.config/whisper-code/settings.json`)
- [x] Env var overrides (`WHISPER_*` prefix, file > defaults priority)
- [x] Grammar checking (optional, POST to chat/completions endpoint)
- [x] Structured logging module (`src/utils/logger.py`, file + console handlers)
- [x] Native macOS toast notifications (`src/utils/toast.py`, osascript-based)
- [x] Transcription confidence score display in HUD (`confidence_changed` signal, `confidence_label`)

### Implemented

- [x] Settings panel UI (Qt dialog with config editing, hotkey recorder)
- [x] Hotkey configuration UI (live capture via pynput in background thread)
- [x] Comprehensive test suite (194 tests, 98% coverage)

---

## V0.1.1 (Stability & Testing)

### Planned

- [x] Core dictation flow (V0.1.0)
- [x] Integration tests (end-to-end with mock API) — `tests/test_integration.py`
- [x] Performance profiling (latency, CPU, memory)
- [x] CI/CD pipeline — `.github/workflows/ci.yml`

### Timeline

- **Development:** 1-2 weeks
- **Release:** Post-integration tests completion

---

## V1.0.0 (Enhancements)

- [x] Auto-stop on silence detection (VAD) — configurable threshold (100-5000ms), speech detection guard (500 RMS threshold)

- [x] Hybrid text injection (AX API first, clipboard+Cmd+V fallback)

---

## V2.0.0 (Quality of Life)

### Implemented

- [x] Voice commands ("undo", "new line", "period", "comma") — `src/utils/voice_commands.py`
  - Punctuation injection ("comma", "period", "new line")
  - Undo command with backspace simulation
  - Configurable via settings dialog checkbox
  - Full test coverage (18 tests)
- [x] Model quality selector (fast / balanced / accurate)

### Planned

- [ ] Wake word activation ("Hey Whisper")
- [ ] Custom Whisper model loading
- [ ] Model quality selector (fast / balanced / accurate)

### Timeline

- **Development:** 4-5 weeks
- **Release:** Q2 2027

---

## V3.0.0 (Vision)

### Planned

- [ ] Cloud fallback for non-Apple Silicon Macs
- [ ] iOS support (iPad dictation)
- [ ] Voice profiles (personalize accuracy per user)
- [ ] Integration with third-party apps (Slack, Notion, etc.)
- [ ] Plugin system for custom post-processing
- [ ] Export transcriptions to Markdown/TXT
- [ ] Collaborative dictation (multiple microphones)

### Timeline

- **Development:** Ongoing
- **Release:** 2028+

---

## Technical Debt

### Immediate

- [x] Write unit tests (16 test files, 194+ tests passing)
- [x] Add integration tests (audio → transcript → injection) — `tests/test_integration.py`
- [x] Add CI/CD pipeline (`.github/workflows/ci.yml`)

### Short-term

- [x] **Improve test coverage** (current: 98% / 194 tests)
  - `wave_overlay.py` — 99% (timer animation, line 59)
  - `api_transcriber.py` — 99% (error paths, line 48)
  - `__main__.py` — 67% (entry point, line 4)
  - `grammar_checker.py` — 100%
  - `settings_dialog.py` — 91% (hotkey recorder, lines 49-53, 58-60, 189-192)
- [x] Profile performance (CPU, memory, latency)
- [ ] Add memory leak detection (PyAudio stream lifecycle)
- [ ] Improve error messages (toast notifications already implemented)

### Long-term

- [ ] Migrate from PyAudio to sounddevice (if needed)
- [ ] Consider switching to PyQt6
- [ ] Add type hints across entire codebase
- [ ] Implement config schema validation (Pydantic)

---

## Dependencies

| Dependency | Current | Notes |
|-----------|---------|-------|
| Python | 3.14+ | Per pyproject.toml |
| PyQt5 | 5.15.11+ | Menu bar + HUD |
| PyAudio | 0.2.14+ | Audio capture |
| requests | 2.31+ | HTTP client for oMLX API |
| pyperclip | 1.11+ | Clipboard backup/restore |
| pynput | 1.8+ | Global hotkey listener |
| numpy | 1.26+ | RMS calculation |
| pytest | 9.0+ | Testing framework |
| pytest-cov | 5.0+ | Coverage reporting |
| responses | 0.25+ | API mocking for integration tests |
| oMLX | Required | Local STT server (not a pip dependency) |

---

## Release Strategy

1. **Alpha:** Internal testing, unstable APIs
2. **Beta:** Feature complete, bug fixes
3. **Release Candidate:** Frozen features, final testing
4. **Stable:** Public release, documented APIs

---

## Feedback Loop

- Collect user feedback via GitHub issues
- Track performance metrics (latency, accuracy, CPU)
- Monitor error rates (crashes, timeouts)
- Prioritize features based on user demand
