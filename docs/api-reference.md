# API Reference

Module interfaces and public APIs for Whisper-Code.

---

## `src/gui/tray_menu.py`

Menu bar status icon handler with dropdown items and Settings panel trigger.

### `class TrayMenu`

```python
class TrayMenu(QSystemTrayIcon):
    """System tray icon controller for macOS."""

    def __init__(self, parent: QObject = None) -> None:
        """Initialize the tray icon and its context menu."""
        ...

    def set_status(self, status: str) -> None:
        """Update the menu bar icon based on app state.

        Args:
            status: One of 'idle', 'listening', 'processing'.
        """
        ...
```

### Signals

| Signal | Emitted When |
|--------|-------------|
| `settings_requested` | User clicks Settings in menu |
| `quit_requested` | User clicks Quit in menu |

---

## `src/gui/wave_overlay.py`

Translucent overlay HUD display displaying microphone input wave visualization.

### `class WaveOverlay`

```python
class WaveOverlay(QWidget):
    """Floating transparent window showing dynamic waveform level."""

    def __init__(self, parent: QWidget = None) -> None:
        """Initialize the translucent overlay widget."""
        ...

    def show_overlay(self) -> None:
        """Fade in and display the overlay."""
        ...

    def hide_overlay(self) -> None:
        """Fade out and hide the overlay."""
        ...

    def update_wave_level(self, level: float) -> None:
        """Update waveform animation bar heights.

        Args:
            level: Float from 0.0 to 1.0 representing audio volume.
        """
        ...
```

---

## `src/core/hotkey_listener.py`

Global hotkey key interception using `pynput`.

### `class HotkeyListener`

```python
class HotkeyListener:
    """Listens for global keyboard shortcuts to trigger dictation."""

    def __init__(self, hotkey_sequence: str, callback: Callable) -> None:
        """Initialize the listener.

        Args:
            hotkey_sequence: Key sequence (e.g., 'Option+Option').
            callback: Function to invoke when shortcut is triggered.
        """
        ...

    def start(self) -> None:
        """Start background keyboard hook thread."""
        ...

    def stop(self) -> None:
        """Terminate keyboard hook thread."""
        ...
```

### Events

| Event | Trigger |
|-------|---------|
| `hotkey_pressed` | User presses the registered hotkey |
| `hotkey_released` | User releases the hotkey |
| `mouse_click` | User clicks outside the app window |

---

## `src/core/mlx_transcriber.py`

Speech-to-text transcriber thread utilizing MLX Whisper.

### `class MLXTranscriber`

```python
class MLXTranscriber(QThread):
    """Asynchronous worker thread for local Whisper model inference."""

    # PyQt Signals for communication with main UI thread
    transcription_complete = pyqtSignal(str)
    transcription_failed = pyqtSignal(str)

    def __init__(self, model_size: str = "large-v3-turbo", eco_mode: bool = False) -> None:
        """Initialize worker thread.

        Args:
            model_size: Whisper model size designation.
            eco_mode: Whether to release model weights when idle.
        """
        ...

    def load_model(self) -> None:
        """Load target Whisper model weights into unified memory."""
        ...

    def run(self) -> None:
        """Initiate transcription inference on recorded audio buffer."""
        ...

    def unload_model(self) -> None:
        """Explicitly clear model memory weights (Eco Mode)."""
        ...
```

### Errors

| Exception | Raised When |
|-----------|------------|
| `ModelLoadError` | Model fails to load |
| `AudioFormatError` | Audio data is invalid format |
| `InferenceError` | Whisper inference fails |

---

## `src/core/audio_recorder.py`

Thread-safe audio recording using PyAudio.

### `class AudioRecorder`

```python
class AudioRecorder:
    """Handles raw microphone input buffering in memory."""

    def __init__(self, sample_rate: int = 16000) -> None:
        """Initialize recorder settings.

        Args:
            sample_rate: Hz sampling frequency.
        """
        ...

    def start_recording(self) -> None:
        """Open audio stream and begin appending to buffer."""
        ...

    def stop_recording(self) -> bytes:
        """Close audio stream and return complete raw audio bytes buffer."""
        ...

    def get_rms_level(self) -> float:
        """Compute Root-Mean-Square (RMS) amplitude level.

        Returns:
            Normalized amplitude float (0.0 to 1.0).
        """
        ...
```

---

## `src/utils/text_injector.py`

Clipboard backup, injection, and restoration service.

### `class TextInjector`

```python
class TextInjector:
    """Handles automated pasting into focused application without destroying clipboard history."""

    def __init__(self) -> None:
        """Initialize the text injector."""
        ...

    def inject_text(self, text: str) -> bool:
        """Injects text at active cursor by backup-paste-restore routine.

        Args:
            text: Text string to paste.

        Returns:
            True if text injection succeeded.
        """
        ...
```

---

## `main.py`

Application entry point.

```python
def main() -> None:
    """Entry point for the Whisper-Code application."""
    ...

if __name__ == "__main__":
    main()
```

---

## Configuration Schema

```json
{
    "hotkey": {
        "key": "Option",
        "repeat": true
    },
    "language": "en-US",
    "sensitivity": "medium",
    "sample_rate": 16000,
    "auto_insert": true,
    "eco_mode": false,
    "model_size": "large-v3-turbo"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `hotkey.key` | string | "Option" | Hotkey to trigger dictation |
| `hotkey.repeat` | boolean | true | Double-tap behavior |
| `language` | string | "en-US" | Input language |
| `sensitivity` | string | "medium" | Mic sensitivity (low/medium/high) |
| `sample_rate` | integer | 16000 | Audio sample rate |
| `auto_insert` | boolean | true | Auto-copy to clipboard |
| `eco_mode` | boolean | false | Release model from RAM when idle |
| `model_size` | string | "large-v3-turbo" | Whisper model designation |

---

## Data Flow

```
User Input (click/hotkey)
    ↓
InputManager detects activation
    ↓
AudioProcessor starts capturing
    ↓
MLXEngine receives audio chunks
    ↓
MLXEngine transcribes to text
    ↓
TextInjector copies to clipboard
    ↓
Text appears in active window
```
