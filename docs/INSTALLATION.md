# Installation Guide

This guide covers installation and setup for **Whisper-Code** on macOS.

---

## Pre-Installation Checklist

Before installing, ensure you have:

- [ ] **macOS** (Optimized for Apple Silicon).
- [ ] **Python 3.14+** installed.
- [ ] **uv** installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- [ ] A local **OpenAI-compatible API** running (e.g., oMLX) at `http://localhost:8080`.

---

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd whisper-code
```

### 2. Install Dependencies

Whisper-Code uses `uv` for lightning-fast, reproducible dependency management.

```bash
uv sync
```

### 3. Grant macOS Permissions

Whisper-Code requires two permissions to function:

#### Microphone Permission

- The first time you record, macOS will prompt for Microphone access.
- You can also manually enable it in **System Settings** → **Privacy & Security** → **Microphone**.

#### Accessibility Permission

- Required for the global hotkey (`Cmd+Ctrl+T`) and text injection.
- Open **System Settings** → **Privacy & Security** → **Accessibility**.
- Find your terminal (e.g., iTerm, Terminal, or VS Code) and toggle it **On**.

---

## Configuration

Settings are stored in `~/.config/whisper-code/settings.json`. It is created automatically on the first run.

```json
{
    "api_url": "http://localhost:8080",
    "model_name": "whisper-large-v3",
    "sample_rate": 16000
}
```

- **api_url**: Base URL of your local oMLX/OpenAI server.
- **model_name**: The model identifier (default: `whisper-large-v3`).

---

## Running the Application

```bash
uv run main.py
```

Check your macOS menu bar for the **green circle icon**. You're ready to go!

---

## Building a Standalone .app

```bash
bash scripts/build-mac.sh --patch --build
```

This creates `dist/Whisper-Code.app`. Without a Developer ID certificate, macOS will show a warning on first launch. Bypass by right-clicking the app → Open → Open.

## Versioning

```bash
bash scripts/build-mac.sh --major    # 0.1.0 → 1.0.0
bash scripts/build-mac.sh --minor    # 0.1.0 → 0.2.0
bash scripts/build-mac.sh --patch    # 0.1.0 → 0.1.1
bash scripts/build-mac.sh --build    # Build without version bump
```

Each version bump creates a git tag (`vX.Y.Z`) and updates `CHANGELOG.md`.

---

## Troubleshooting

| Issue | Solution |
|-------| :--- |
| `ModuleNotFoundError` | Ensure you ran `uv sync` and are using `uv run main.py`. |
| Hotkey not working | Verify **Accessibility** permissions for your terminal. |
| No text injected | Ensure the application you want to type in is focused before/during dictation. |
| API Error | Ensure your oMLX server is running at the URL specified in settings. |
