from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QCursor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

# Click reasons that should reveal the menu. Unknown/MiddleClick are
# deliberately excluded: popping a menu for them fights the user's intent.
MENU_REASONS: frozenset[QSystemTrayIcon.ActivationReason] = frozenset(
    {
        QSystemTrayIcon.ActivationReason.Trigger,
        QSystemTrayIcon.ActivationReason.DoubleClick,
        QSystemTrayIcon.ActivationReason.Context,
    }
)

ToggleCallback = Callable[[], None]
StopCallback = Callable[[], None]
QuitCallback = Callable[[], None]
SettingsCallback = Callable[[], None]


class TrayMenu(QSystemTrayIcon):
    """Create a macOS system tray menu with toggle and quit actions.

    Provides a system tray icon with a menu containing a toggle
    action (to start/stop listening) and a quit action.

    The menu is *not* handed to ``setContextMenu()``. On macOS that makes
    libqcocoa's ``QStatusItemDelegate`` observe the NSStatusItem menu's
    begin-tracking notification, and that handler reads ``clickCount`` off
    ``[NSApp currentEvent]``. ``-[NSEvent clickCount]`` is only valid for
    mouse events, so when a system-defined event (Fn/Globe or a media key)
    happens to be current, AppKit raises ``NSInternalInconsistencyException``
    ("Invalid message sent to event ... type=SysDefined") and the process
    aborts. Instead the menu is popped by us from the ``activated`` signal,
    one event-loop tick later, so Qt never installs that observer and no
    foreign event is current while the menu starts tracking.
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

        self.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle a click on the tray icon by scheduling the menu.

        The popup is deferred to the next event-loop tick rather than shown
        inline: while this callback runs ``[NSApp currentEvent]`` is still the
        event that triggered the activation, and starting menu tracking
        against a non-mouse current event is what crashes AppKit.

        Args:
            reason: Why Qt reports the tray icon was activated.
        """
        if reason in MENU_REASONS:
            QTimer.singleShot(0, self._show_menu)

    def _show_menu(self) -> None:
        """Pop the menu just below the tray icon.

        Falls back to the cursor position when the icon reports a null
        geometry, which happens while the status bar item has not been laid
        out yet or is hidden behind the notch.
        """
        rect: QRect = self.geometry()
        # bottomLeft() is the *last* row inside the icon; add one to clear it.
        anchor: QPoint = (
            QPoint(rect.left(), rect.bottom() + 1) if not rect.isNull() else QCursor.pos()
        )
        self.menu.popup(anchor)

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
