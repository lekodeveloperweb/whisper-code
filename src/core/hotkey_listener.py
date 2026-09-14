from __future__ import annotations

import logging
from typing import Any

from pynput import keyboard
from PySide6.QtCore import QObject
from PySide6.QtCore import Signal as pyqtSignal

logger = logging.getLogger("whisper")


class HotkeyListener(QObject):
    """Listen for global keyboard hotkeys in a background thread.

    Monitors for the configured hotkey (default Cmd+Ctrl+T) which
    triggers the listening action, and Enter which stops recording.
    """

    triggered = pyqtSignal()
    confirmed = pyqtSignal()

    def __init__(self) -> None:
        """Initialize the hotkey listener with default hotkey."""
        super().__init__()
        self.listener: keyboard.Listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._modifiers: set[Any] = set()
        self.hotkey_str: str = "Cmd+Ctrl+T"

    def _on_press(self, key: Any) -> None:
        """Process a key press event.

        Tracks modifier keys and detects the configured hotkey.
        Emits triggered signal when hotkey is pressed.

        Args:
            key: The keyboard key that was pressed.
        """
        if key in [
            keyboard.Key.cmd,
            keyboard.Key.cmd_l,
            keyboard.Key.cmd_r,
            keyboard.Key.ctrl,
            keyboard.Key.ctrl_l,
            keyboard.Key.ctrl_r,
        ]:
            self._modifiers.add(key)
            return

        is_cmd: bool = any(
            k in self._modifiers for k in [keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r]
        )
        is_ctrl: bool = any(
            k in self._modifiers
            for k in [keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r]
        )

        if is_cmd and is_ctrl and hasattr(key, "char") and key.char and key.char.lower() == "t":
            self.triggered.emit()
            return

        if key == keyboard.Key.enter:
            self.confirmed.emit()

    def _on_release(self, key: Any) -> None:
        """Process a key release event.

        Removes modifier keys from the tracked set.

        Args:
            key: The keyboard key that was released.
        """
        if (
            key
            in [
                keyboard.Key.cmd,
                keyboard.Key.cmd_l,
                keyboard.Key.cmd_r,
                keyboard.Key.ctrl,
                keyboard.Key.ctrl_l,
                keyboard.Key.ctrl_r,
            ]
            and key in self._modifiers
        ):
            self._modifiers.remove(key)

    def start(self) -> None:
        """Start listening for global hotkeys in a background thread.

        Logs the configured hotkey and that Enter is listened for.
        """
        logger.info(f"Listening for global hotkey: {self.hotkey_str}")
        logger.info("Listening for ENTER to stop recording.")
        self.listener.start()

    def stop(self) -> None:
        """Stop the global hotkey listener."""
        self.listener.stop()
