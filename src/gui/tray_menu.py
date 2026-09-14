from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

ToggleCallback = Callable[[], None]
StopCallback = Callable[[], None]
QuitCallback = Callable[[], None]
SettingsCallback = Callable[[], None]


class TrayMenu(QSystemTrayIcon):
    """Create a macOS system tray menu with toggle and quit actions.

    Provides a system tray icon with a menu containing a toggle
    action (to start/stop listening) and a quit action. Also
    supports double-click to toggle.
    """

    def __init__(
        self,
        toggle_callback: ToggleCallback,
        stop_callback: StopCallback,
        quit_callback: QuitCallback,
        settings_callback: SettingsCallback | None = None,
        version: str = "unknown",
    ) -> None:
        """Initialize the tray menu with action callbacks.

        Args:
            toggle_callback: Callback for the toggle/listen action.
            stop_callback: Callback for the stop action.
            quit_callback: Callback for the quit action.
            settings_callback: Optional callback for settings.
            version: Application version string for the menu.
        """
        super().__init__()

        icon: QIcon = QIcon.fromTheme("audio-input-microphone")

        if icon.isNull():
            icon = self._create_microphone_icon()

        self.setIcon(icon)
        self.setToolTip("Whisper-Code")

        self.menu: QMenu = QMenu()

        self.start_action: QAction = QAction("Start Dictation  ⌘ ^ T", self)
        self.start_action.triggered.connect(toggle_callback)
        self.menu.addAction(self.start_action)

        self.stop_action: QAction = QAction("Stop Dictation  Enter", self)
        self.stop_action.triggered.connect(stop_callback)
        self.stop_action.setVisible(False)
        self.menu.addAction(self.stop_action)

        self.menu.addSeparator()

        self.settings_action: QAction | None = None
        if settings_callback is not None:
            self.settings_action = QAction("&Settings...", self)
            self.settings_action.triggered.connect(settings_callback)
            self.menu.addAction(self.settings_action)

        self.menu.addSeparator()

        self.version_action: QAction = QAction(f"v{version}", self)
        self.version_action.setDisabled(True)
        self.menu.addAction(self.version_action)

        quit_action: QAction = QAction("Quit", self)
        quit_action.triggered.connect(quit_callback)
        self.menu.addAction(quit_action)

        self.setContextMenu(self.menu)

    def _create_microphone_icon(self) -> QIcon:
        """Draw a microphone icon programmatically for macOS system tray.

        Returns:
            A QIcon with a drawn microphone icon.
        """
        size: int = 64
        pixmap: QPixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter: QPainter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color: QColor = QColor(255, 255, 255)

        head: QRect = QRect(21, 10, 22, 26)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(head, 11, 11)

        body: QRect = QRect(25, 36, 14, 20)
        painter.setPen(QColor(255, 255, 255, 128))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(body)

        painter.end()
        return QIcon(pixmap)

    def update_state(self, is_listening: bool = False, is_processing: bool = False) -> None:
        """Update the tray menu state based on the current mode.

        Shows/hides the stop action and updates the toggle action text.

        Args:
            is_listening: Whether currently recording audio.
            is_processing: Whether currently processing transcription.
        """
        if is_listening:
            self.stop_action.setVisible(True)
            self.start_action.setVisible(False)
            self.setToolTip("Listening...")
        elif is_processing:
            self.stop_action.setVisible(False)
            self.start_action.setVisible(False)
            self.setToolTip("Transcribing...")
        else:
            self.stop_action.setVisible(False)
            self.start_action.setVisible(True)
            self.setToolTip("Idle")

    def show(self) -> None:
        """Show the system tray icon."""
        super().show()
