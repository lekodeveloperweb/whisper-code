# 📜 Product Requirements Document (PRD)

**Product Name:** Whisper-Code
**Version:** 1.0 (Minimum Viable Product - MVP)
**Date:** 2026-05-30

## 1. 🎯 Goals and Vision

**Goal:** To provide a fast, discreet, and highly accessible voice dictation tool that allows users to convert spoken words into text and seamlessly insert them into any focused application (e.g., text editors, browsers) without requiring keyboard interaction.

**Vision:** To create a background dictation utility that feels as native and smooth as built-in OS features.

## 2. 👤 Target Audience

* Users with mobility challenges.
* Professionals who need to take rapid notes during meetings or while driving (where hands are full).
* Developers or writers looking for hands-free productivity.

## 3. ✨ Core Features (MVP Scope)

| ID | Feature | Description | Priority |
| :--- | :--- | :--- | :--- |
| **F1** | **GUI Indicator** | A macOS Menu Bar App with a status icon, plus a translucent on-screen overlay when listening. | High |
| **F2** | **Listening State Visualization** | The menu bar icon changes state and the overlay displays a dynamic wave animation when listening. | High |
| **F3** | **Manual Activation (Click)** | Clicking the menu bar status icon starts/stops listening. | High |
| **F4** | **Automatic Activation (Hotkey)** | A configurable global keyboard shortcut (e.g., Double Tap Option Key) starts/stops listening regardless of the application's focus. | High |
| **F5** | **Speech Recognition** | Captures audio input and accurately transcribes it using the specified Whisper model. | Critical |
| **F6** | **Cursor Insertion** | The recognized text is automatically copied to the system clipboard and then injected into the currently active text field. | Critical |
| **F7** | **Error Handling** | Provides basic visual feedback if the microphone is unavailable or if the STT model fails to transcribe. | Medium |

## 4. ⚙️ Non-Functional Requirements (NFRs)

* **Performance:** Transcription latency must be minimized for a natural user experience (Target: < 3 seconds for a 10-second utterance).
* **Resource Efficiency:** The application must run with low CPU and memory overhead when idle.
* **Robustness:** Must handle interruptions (e.g., user pressing Escape key while listening).
* **Security/Privacy:** Audio recordings must be processed locally and not sent to external servers.

## 5. 📋 Success Metrics (KPIs)

* **Transcription Latency:** < 500ms from audio end to text output
* **Transcription Accuracy:** > 90% (for clear speech in quiet environment)
* **CPU Usage:** < 15% when actively listening, < 5% when idle
* **Memory Usage (Warm Standby):** < 2.0GB (Whisper Large V3 Turbo loaded in FP16 for fast execution)
* **Memory Usage (Eco Mode):** < 250MB when idle (model loaded on-demand, causing 2-3s delay on first run)
* **System Response:** No UI freezing during audio processing

## 6. ⚠️ Edge Cases & Error Scenarios

| Scenario | Expected Behavior |
|----------| :--- |
| Microphone unavailable / permission denied | Show "Mic unavailable" toast notification, disable listening |
| Background noise > threshold | Reduce confidence score, show warning in GUI |
| STT timeout (no result after buffer) | Retry with longer buffer or show "No speech detected" |
| STT model error | Show "Model error" toast, suggest restarting the app |
| Clipboard permission denied (macOS) | Show warning, offer to copy to file instead |
| Clipboard overwrite | Backup existing clipboard, paste transcribed text, and restore backup after delay |
| User interruption during listening | Immediately stop, discard current buffer |
| Active window not editable | Show warning, keep transcription on clipboard |

## 7. 📖 User Stories

* **US1:** As a user, I want to activate dictation by clicking the microphone icon so I can start speaking hands-free.
* **US2:** As a user, I want to activate dictation with a global hotkey (e.g., Double Tap Option) so I can trigger it without moving my mouse.
* **US3:** As a user, I want to see visual feedback when the app is listening so I know when to speak.
* **US4:** As a user, I want the transcribed text to appear in my active text editor automatically so I don't have to switch windows.
* **US5:** As a user, I want to stop dictation at any time with a key press so I don't keep speaking unnecessarily.
* **US6:** As a user, I want to configure the hotkey and sensitivity settings so the app works for my workflow.

## 8. 🔒 Technical Constraints & Assumptions

* **OS Support:** macOS (primary focus), Windows, Linux (optional)
* **Python version:** 3.10+
* **Available RAM:** 2GB minimum for model loading
* **Microphone:** USB or built-in (48kHz+ sampling rate, 16-bit)
* **Network:** Not required (all processing local), but optional for model download
* **Accessibility:** Keyboard-only navigation supported
* **Language:** English (MVP), multi-language support (V2)

## 9. 📐 Technical Trade-offs

| Decision | Rationale |
|----------| :--- |
| Local processing (MLX) | Privacy first, no cloud dependency |
| PyQt5 over Tkinter | Better system tray and translucent overlay support |
| Warm Standby vs Eco Mode | Trade-off between high RAM usage (~1.6GB) and low startup latency (<500ms) |
| Clipboard Paste & Restore | Pastes text automatically via keyboard simulation while preserving original clipboard |
| Menu Bar + Overlay | Floating window is obtrusive; status bar + floating overlay is native-like |
| Model Quality Selection | Let users choose Tiny/Base/Small/Large models to match their hardware |

## 10. 🏗️ Technical Architecture

See [System Architecture Diagram](docs/system-architecture-diagram.md) for detailed component breakdown and system design.

## 11. ⏭️ Future Enhancements (V2.0+)

* **Continuous Dictation:** The app remains listening until stopped by a specific command (e.g., "Stop").
* **Command Detection:** Integration of wake words ("Hey VoiceFocus") to trigger activation.
* **Language Selection:** Allowing the user to specify the input language.
* **History Log:** Storing and viewing past transcribed sessions.essions.
