"""Whisper-Code: Voice dictation application entry point.

Entry point for the macOS menu bar app. Wires up all subsystems,
starts the PyQt event loop.

Run via:
    uv run whisper          (console script)
    python -m src.whisper_code  (module entry point)
"""

from __future__ import annotations

import os
import re
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from src.core.api_transcriber import APITranscriber
from src.core.audio_recorder import AudioRecorder
from src.core.grammar_checker import GrammarChecker
from src.core.hotkey_listener import HotkeyListener
from src.gui.settings_dialog import SettingsDialog
from src.gui.tray_menu import TrayMenu
from src.gui.wave_overlay import WaveOverlay
from src.utils.config_manager import ConfigManager
from src.utils.logger import get_logger
from src.utils.text_injector import TextInjector
from src.utils.toast import ToastNotifier
from src.utils.voice_commands import process_voice_commands
from src.whisper_code import __version__

logger = get_logger()

SILENCE_THRESHOLD_MIN_MS: int = 100
SILENCE_THRESHOLD_MAX_MS: int = 5000


class WhisperCodeApp:
    """macOS menu bar app for hands-free voice dictation.

    Coordinates audio capture, STT transcription, optional grammar
    refinement, and text injection into the focused application.

    Usage::

        app = WhisperCodeApp()
        app.setup()      # Show UI, start listeners
        app.run()        # Enter Qt event loop
    """

    def __init__(self, app: QApplication | None = None) -> None:
        """Initialize subsystems without starting any UI or listeners.

        Call setup() after __init__ to fully start the application.
        This separation enables testing individual components.
        """
        self.app: QApplication = app or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Core subsystems
        self.config: ConfigManager = ConfigManager()
        self.injector: TextInjector = TextInjector()
        self.toast: ToastNotifier = ToastNotifier()

        # Audio & transcription subsystems
        self.recorder: AudioRecorder = self._make_recorder()
        self.transcriber: APITranscriber = self._make_transcriber()
        self.grammar_checker: GrammarChecker = self._make_grammar_checker()

        # UI subsystems
        self.overlay: WaveOverlay = WaveOverlay()
        self.tray: TrayMenu = self._make_tray()
        self.settings_dialog: SettingsDialog | None = None

        # Hotkey subsystem
        self.hotkey: HotkeyListener = self._make_hotkey()

        # Application state
        self.is_listening: bool = False
        self.is_processing: bool = False
        self.rms_timer: QTimer = QTimer()

        self._wire_signals()
        self.setup()

    def _make_recorder(self) -> AudioRecorder:
        """Create AudioRecorder configured from settings."""
        sample_rate = self.config.get("sample_rate")
        return AudioRecorder(sample_rate=int(sample_rate) if sample_rate else 16000)

    def _make_transcriber(self) -> APITranscriber:
        """Create APITranscriber configured with quality-resolved model name."""
        from src.utils.model_quality import resolve_model_name

        api_url: str = str(self.config.get("api_url") or "http://localhost:8080")
        model_quality: str = str(self.config.get("model_quality") or "accurate")
        custom_model_name: str | None = self.config.get("model_name")  # type: ignore[assignment]

        resolved_model: str = resolve_model_name(model_quality, custom_model_name)
        return APITranscriber(api_url, resolved_model)

    def _make_grammar_checker(self) -> GrammarChecker:
        """Create GrammarChecker configured from settings."""
        api_url: str = str(self.config.get("api_url") or "http://localhost:8080")
        grammar_model: str = str(self.config.get("grammar_model") or "gemma4-e4b-8b")
        return GrammarChecker(api_url, grammar_model)

    def _make_tray(self) -> TrayMenu:
        """Create system tray with action callbacks."""
        return TrayMenu(
            self.start_listening,
            self.stop_listening,
            self.quit_app,
            self._open_settings,
            version=__version__,
        )

    def _make_hotkey(self) -> HotkeyListener:
        """Create HotkeyListener (signals wired via _wire_signals)."""
        return HotkeyListener()

    def _wire_signals(self) -> None:
        """Connect all inter-component signals."""
        self.hotkey.triggered.connect(self.start_listening_flow)
        self.hotkey.confirmed.connect(self.stop_listening_flow)
        self.transcriber.finished.connect(self.on_transcription_success)
        self.transcriber.error.connect(self.on_transcription_error)
        self.transcriber.confidence_changed.connect(self.on_confidence)
        self.grammar_checker.finished.connect(self.on_refinement_success)
        self.grammar_checker.error.connect(self.on_refinement_error)

    def setup(self) -> None:
        """Start UI elements and background listeners.

        Must be called after __init__ to fully initialize:
        - Shows the HUD overlay window
        - Shows the system tray icon
        - Starts the global hotkey listener
        - Logs startup configuration
        """
        self._apply_icon()
        self.overlay.show()
        self.tray.show()
        self.hotkey.start()
        self.rms_timer.timeout.connect(self.update_rms)
        self._log_startup()

    def _apply_icon(self) -> None:
        """Load the application icon from the bundled PNG file."""
        icon_path = os.path.join(os.path.dirname(__file__), "src", "gui", "icon.png")
        if os.path.exists(icon_path):
            self.app.setWindowIcon(QIcon(icon_path))

    def _log_startup(self) -> None:
        """Emit startup log with API URL, resolved model, quality setting, and hotkey."""
        from src.utils.model_quality import resolve_model_name

        logger.info("\n" + "=" * 50)
        logger.info("Whisper-Code is running!")
        logger.info(f"API URL: {self.config.get('api_url')}")
        model_quality: str = str(self.config.get("model_quality") or "accurate")
        custom_model: str | None = self.config.get("model_name")  # type: ignore[assignment]
        resolved: str = resolve_model_name(model_quality, custom_model)
        logger.info(f"STT Model:   {resolved} (quality: {model_quality})")
        if self.config.get("use_grammar_check"):
            logger.info(f"SLM Model:   {self.config.get('grammar_model')}")
        logger.info("Hotkey:  Cmd + Ctrl + T")
        logger.info("=" * 50 + "\n")

    def _apply_voice_commands(self, text: str) -> str | tuple[str, str]:
        """Apply voice commands to transcribed text if enabled.

        Args:
            text: Raw transcribed text string.

        Returns:
            Processed text. If "undo" is detected, returns a tuple
            (text, "undo") where text is the processed string and the
            second element signals the undo action.
        """
        if self.config.get("voice_commands_enabled"):
            return process_voice_commands(text, enabled=True)
        return text

    def _handle_undo(self, text: str) -> None:
        """Simulate backspace for the words after 'undo' voice command.

        Args:
            text: The processed text (without 'undo' and trailing words).
        """
        logger.info("Undo command detected — simulating backspace.")
        # Calculate how many characters were removed by comparing lengths
        removed_length = len(text) - len(re.sub(r"\bundo\b\s*", "", text).strip())
        if removed_length > 0:
            self.injector.backspace(removed_length)

    # ── Flow methods ───────────────────────────────────────────────────────

    def start_listening_flow(self) -> None:
        """Triggered by Cmd+Ctrl+T. Starts recording if idle."""
        if not self.is_listening and not self.is_processing:
            logger.debug("Hotkey: Start triggered")
            self.start_listening()

    def stop_listening_flow(self) -> None:
        """Triggered by ENTER. Stops recording if listening."""
        if self.is_listening:
            logger.debug("Hotkey: Stop (Enter) triggered")
            self.stop_listening()

    # ── Action methods ─────────────────────────────────────────────────────

    def start_listening(self) -> None:
        """Begin audio capture when idle.

        Reads silence_threshold from config, clamps to [100, 5000]ms.
        Checks accessibility permission, starts the recorder, shows HUD.
        """
        try:
            logger.info("Starting recording...")
            self._apply_silence_threshold()
            self._check_accessibility_permission()
            self.recorder.start_recording()
            self.is_listening = True
            self.tray.update_state(is_listening=True)
            self.overlay.show_hud("Listening... Press Enter to stop")
            self.rms_timer.start(50)
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.toast.error(str(e))
            self.on_transcription_error(f"Recording Error: {e}")

    def _apply_silence_threshold(self) -> None:
        """Read silence_threshold_ms from config, clamp to valid range."""
        threshold = self.config.get("silence_threshold_ms")
        if threshold is not None and isinstance(threshold, (int, float)):
            clamped = max(
                SILENCE_THRESHOLD_MIN_MS,
                min(int(threshold), SILENCE_THRESHOLD_MAX_MS),
            )
            self.recorder.silence_threshold_ms = clamped

    def _check_accessibility_permission(self) -> None:
        """Check and log Accessibility permission status.

        With hybrid injection, this is informational only — the
        TextInjector handles fallback automatically.
        """
        from src.utils.text_injector import (
            check_accessibility_permission as check_perm,
        )

        if not check_perm():
            logger.debug(
                "UI Automation is disabled. Keyboard simulation will be "
                "unavailable, but AX API injection may still work."
            )

    def stop_listening(self) -> None:
        """Stop audio capture and send to transcription pipeline."""
        logger.info("Stopping recording...")
        self.is_listening = False
        self.rms_timer.stop()

        audio_data = self.recorder.stop_recording()

        if not audio_data:
            logger.info("No speech detected.")
            self.tray.update_state(is_listening=False)
            self.overlay.show_hud("No speech detected")
            QTimer.singleShot(1500, self.overlay.hide_hud)
            return

        logger.info(f"Sending {len(audio_data)} bytes to Whisper...")
        self.is_processing = True
        self.tray.update_state(is_listening=False, is_processing=True)
        self.overlay.show_hud("Transcribing...")

        self.transcriber.set_audio(audio_data)
        self.transcriber.start()

    def update_rms(self) -> None:
        """Pass real-time RMS levels from recorder to HUD visualization.

        Detects if the recorder has auto-stopped (VAD) and triggers
        the transcription pipeline.
        """
        if self.is_listening and not self.recorder.is_recording:
            logger.info("Auto-stop (silence) detected.")
            self.stop_listening()
            return

        rms: float = self.recorder.get_rms()
        self.overlay.set_rms(rms)

    # ── Callback methods ───────────────────────────────────────────────────

    def on_confidence(self, confidence: float) -> None:
        """Forward confidence score to the HUD overlay."""
        self.overlay.set_confidence(confidence)

    def on_transcription_success(self, text: str) -> None:
        """Handle successful transcription - optional grammar check then inject.

        If grammar checking is enabled, sends text through the grammar
        refinement pipeline first. Otherwise injects immediately.
        Voice commands are applied after grammar refinement.
        """
        if not text:
            logger.warning("Transcription result was empty.")
            self.finalize_pipeline(None)
            return

        logger.info(f'Whisper: "{text}"')

        if self.config.get("use_grammar_check"):
            logger.info(f"Sending to {self.config.get('grammar_model')} (grammar refinement)...")
            self.overlay.show_hud("Fixing grammar...")
            self.grammar_checker.set_text(text)
            self.grammar_checker.start()
        else:
            self._finalize_with_voice_commands(text)

    def _finalize_with_voice_commands(self, text: str) -> None:
        """Apply voice commands and finalize the pipeline.

        Args:
            text: Transcribed or grammar-refined text.
        """
        result = self._apply_voice_commands(text)
        if isinstance(result, tuple):
            processed_text, action = result
            if action == "undo":
                self._handle_undo(processed_text)
            self.finalize_pipeline(processed_text)
        else:
            self.finalize_pipeline(result)

    def on_transcription_error(self, error: str) -> None:
        """Handle transcription failure - finalize with None."""
        logger.error(f"Transcription Error: {error}")
        self.toast.error(error)
        self.finalize_pipeline(None)

    def on_refinement_success(self, refined_text: str) -> None:
        """Handle successful grammar refinement - apply voice commands then inject.

        After grammar refinement, voice commands are processed before
        text injection.
        """
        logger.info(f'Grammar refined: "{refined_text}"')
        self._finalize_with_voice_commands(refined_text)

    def on_refinement_error(self, error: str) -> None:
        """Handle grammar check failure - fall back to raw transcription."""
        logger.error(f"Refinement Error: {error}")
        self.toast.error(error)
        logger.warning("Falling back to raw transcription.")
        raw_text = getattr(self.transcriber, "last_result", "")
        if raw_text:
            self.finalize_pipeline(raw_text)
        else:
            self.finalize_pipeline(None)

    def finalize_pipeline(self, text: str | None) -> None:
        """Complete the transcription pipeline and inject text.

        Resets state, injects text if available, hides the HUD.
        """
        self.is_processing = False
        self.tray.update_state(is_listening=False)

        if text:
            logger.info("Injecting text into active window...")
            self.injector.inject_text(text)
            self.overlay.show_hud("Sent!")
            QTimer.singleShot(2000, self.overlay.hide_hud)
        else:
            self.overlay.hide_hud()

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def quit_app(self) -> None:
        """Cleanup and exit the application."""
        self.hotkey.stop()
        if self.is_listening:
            self.recorder.stop_recording()
        self.app.quit()

    def _open_settings(self) -> None:
        """Open the settings dialog if not already visible."""
        if self.settings_dialog is not None and self.settings_dialog.isVisible():
            return
        self.settings_dialog = SettingsDialog(self.config, on_saved=self._on_settings_saved)
        self.settings_dialog.show()

    def _on_settings_saved(self) -> None:
        """Re-apply settings to all subsystems after a config save."""
        self.config.reload()
        self._apply_settings()
        logger.info("Settings applied from UI")

    def _apply_settings(self) -> None:
        """Reconfigure all subsystems from current config values."""
        self._apply_sample_rate()
        self._apply_api_url()
        self._apply_model_config()
        self._apply_grammar_config()
        self._apply_hotkey()
        self._apply_silence_threshold()

    def _apply_sample_rate(self) -> None:
        """Update sample rate if changed."""
        sample_rate = self.config.get("sample_rate")
        new_rate = int(sample_rate) if sample_rate else 16000
        if new_rate != self.recorder.sample_rate:
            logger.debug(f"Sample rate changed: {self.recorder.sample_rate} -> {new_rate}")
            self.recorder.sample_rate = new_rate

    def _apply_api_url(self) -> None:
        """Update API URL if changed."""
        new_url = str(self.config.get("api_url") or "http://localhost:8080")
        if new_url != self.transcriber.base_url:
            logger.debug(f"API URL changed to: {new_url}")
            self.transcriber.base_url = new_url
            self.transcriber.api_endpoint = f"{new_url.rstrip('/')}/v1/audio/transcriptions"

    def _apply_model_config(self) -> None:
        """Update STT model name if changed."""
        from src.utils.model_quality import resolve_model_name

        model_quality: str = str(self.config.get("model_quality") or "accurate")
        custom_model: str | None = self.config.get("model_name")  # type: ignore[assignment]
        resolved = resolve_model_name(model_quality, custom_model)
        if resolved != self.transcriber.model_name:
            logger.debug(f"STT model changed to: {resolved}")
            self.transcriber.model_name = resolved

    def _apply_grammar_config(self) -> None:
        """Update grammar checker config if changed."""
        new_grammar_url = str(self.config.get("api_url") or "http://localhost:8080")
        new_grammar_model = str(self.config.get("grammar_model") or "gemma4-e4b-8b")
        expected_endpoint = f"{new_grammar_url.rstrip('/')}/v1/chat/completions"
        if expected_endpoint != self.grammar_checker.api_endpoint:
            logger.debug(f"Grammar API URL changed to: {expected_endpoint}")
            self.grammar_checker.api_endpoint = expected_endpoint
        if new_grammar_model != self.grammar_checker.model_name:
            logger.debug(f"Grammar model changed to: {new_grammar_model}")
            self.grammar_checker.model_name = new_grammar_model

    def _apply_hotkey(self) -> None:
        """Update hotkey display string if changed."""
        new_hotkey = str(self.config.get("hotkey") or "Cmd+Ctrl+T")
        if new_hotkey != self.hotkey.hotkey_str:
            logger.debug(f"Hotkey display changed to: {new_hotkey}")
            self.hotkey.hotkey_str = new_hotkey

    def run(self) -> int:
        """Run the Qt event loop. Returns the exit code."""
        return self.app.exec_()


def main() -> int:
    """Application entry point. Sets up logging and runs the app."""
    from src.utils.logger import setup_logger

    if sys.stdout.isatty():
        setup_logger(level="DEBUG")
    else:
        setup_logger(level="INFO")

    app = WhisperCodeApp()
    return app.run()
