from __future__ import annotations

import logging
import subprocess
import time

import pyperclip
from pynput.keyboard import Controller, Key

logger = logging.getLogger("whisper")


def check_accessibility_permission() -> bool:
    """Check if UI Automation is enabled (required for keyboard simulation).

    Returns:
        True if UI Automation is enabled, False otherwise.
    """
    try:
        result = subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "System Events" to get UI elements enabled',
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.stdout.strip().lower() == "true"
    except Exception:
        return False


def open_accessibility_settings() -> None:
    """Open the macOS Accessibility settings panel directly."""
    subprocess.run(
        [
            "open",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
        ],
        capture_output=True,
        check=False,
    )


class TextInjector:
    """Inject text into the focused application via clipboard + keyboard shortcut.

    Uses pyperclip to backup/restore clipboard content and pynput to
    simulate keyboard shortcuts. Falls back to clipboard-only injection
    when UI Automation is disabled.
    """

    def __init__(self) -> None:
        """Initialize with a pynput keyboard controller."""
        self.keyboard: Controller = Controller()

    def inject_text(self, text: str | None) -> None:
        """Inject text into the focused application.

        Tries the macOS Accessibility API first (no clipboard
        contamination), then falls back to clipboard + Cmd+V
        keyboard simulation for broader compatibility.

        Checks accessibility permission first. If disabled, falls
        back to clipboard-only injection.

        Args:
            text: The text to inject, or None to skip injection.
        """
        if not text:
            return

        if not check_accessibility_permission():
            logger.warning(
                "UI Automation is disabled. "
                "Open System Settings to Privacy to Accessibility and enable Whisper-Code."
            )
            self._fallback_inject(text)
            return

        # Try AX API first (no clipboard contamination), fall back to Cmd+V
        from src.utils.ax_injector import inject_via_ax_api

        if inject_via_ax_api(text):
            logger.debug("Text injected via Accessibility API.")
            return

        logger.debug("AX API injection failed, falling back to clipboard+Cmd+V.")
        self._inject_with_keyboard(text)

    def _inject_with_keyboard(self, text: str) -> None:
        """Inject text using keyboard shortcut (Cmd+V).

        Backs up clipboard, sets text, simulates Cmd+V, restores clipboard.

        Args:
            text: The text to inject.
        """
        old_clipboard: str = pyperclip.paste()
        pyperclip.copy(text)
        with self.keyboard.pressed(Key.cmd):
            self.keyboard.press("v")
            self.keyboard.release("v")
        time.sleep(0.1)
        pyperclip.copy(old_clipboard)

    def _fallback_inject(self, text: str) -> None:
        """Inject text using clipboard only (no keyboard simulation).

        Args:
            text: The text to inject.
        """
        logger.info("Using clipboard fallback (no Accessibility permission).")
        pyperclip.copy(text)
        time.sleep(0.5)

    def backspace(self, count: int = 1) -> None:
        """Simulate backspace key presses.

        Args:
            count: Number of backspace key presses to simulate.
        """
        for _ in range(count):
            self.keyboard.press(Key.backspace)
            self.keyboard.release(Key.backspace)
