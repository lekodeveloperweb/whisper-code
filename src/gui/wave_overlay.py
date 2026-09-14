from __future__ import annotations

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

BAR_COUNT: int = 7
MAX_BAR_HEIGHT: int = 60
BAR_SPACING: int = 12
BAR_WIDTH: int = 10
WINDOW_HEIGHT: int = 140
WINDOW_WIDTH: int = 440
BASE_Y_OFFSET: int = 30


class WaveOverlay(QWidget):
    """HUD overlay for displaying listening state and waveform visualization.

    Uses a Qt.ToolTip window to avoid focus-switching issues on macOS.
    Renders animated waveform bars based on real-time RMS levels from
    the audio recorder. Fades in/out via window opacity animation.
    """

    def __init__(self) -> None:
        """Initialize the HUD overlay with tooltip flags and translucent background."""
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.setWindowOpacity(0.0)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.layout: QVBoxLayout = QVBoxLayout()  # type: ignore[assignment]
        self.label: QLabel = QLabel("Listening...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Helvetica Neue", 14, QFont.Weight.Bold))
        self.label.setStyleSheet("color: white; margin-bottom: 5px;")
        self.layout.addWidget(self.label)
        self.confidence_label: QLabel = QLabel("")
        self.confidence_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.confidence_label.setFont(QFont("Helvetica Neue", 10, QFont.Weight.Bold))
        self.confidence_label.setStyleSheet("color: rgba(255, 255, 255, 160); margin-top: 2px;")
        self.layout.addWidget(self.confidence_label)
        self.setLayout(self.layout)

        self._rms: float = 0.0
        self._animation_timer: QTimer = QTimer()
        self._animation_timer.timeout.connect(self.update)

        self._center_on_screen()

    def _center_on_screen(self) -> None:
        """Position the HUD centered horizontally near the bottom of the primary screen."""
        screen: QRect = QApplication.primaryScreen().geometry()
        x: int = (screen.width() - self.width()) // 2
        y: int = screen.height() - self.height() - 150
        self.move(x, y)

    def set_rms(self, rms: float) -> None:
        """Set the normalized RMS level for waveform bar rendering."""
        normalized: float = min(rms / 2000.0, 1.0)
        self._rms = normalized

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the HUD background and animated waveform bars.

        Renders a rounded rectangle background and 7 waveform bars
        whose height varies based on the current RMS level.
        """
        if self.windowOpacity() == 0:
            return

        painter: QPainter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(20, 20, 20, 180)))
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 20, 20)

        max_bar_height: int = 40
        spacing: int = 10
        bar_width: int = 8
        center_x: int = self.width() // 2
        base_y: int = self.height() - 30
        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(BAR_COUNT):
            variation: float = (
                0.5 + 0.5 * abs((i - (BAR_COUNT // 2)) / (BAR_COUNT // 2)) if BAR_COUNT > 1 else 1.0
            )
            h: int = int(max_bar_height * self._rms * variation)
            h = max(h, 4)
            x: int = center_x + (i - BAR_COUNT // 2) * (bar_width + spacing) - bar_width // 2
            y: int = base_y - h // 2

            # Height-based gradient: green (low) → blue (mid) → orange → red (high)
            ratio: float = h / max_bar_height if max_bar_height > 0 else 0.0
            if ratio < 0.33:
                color: QColor = QColor(76, 175, 80, 220)  # green
            elif ratio < 0.66:
                color = QColor(33, 150, 243, 220)  # blue
            elif ratio < 0.85:
                color = QColor(255, 152, 0, 220)  # orange
            else:
                color = QColor(244, 67, 54, 220)  # red

            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(QRect(x, y, bar_width, h), bar_width // 2, bar_width // 2)

    def show_hud(self, text: str = "Listening...") -> None:
        """Fade in the HUD by setting opacity to 1.0 and starting animation."""
        self.label.setText(text)
        self.setWindowOpacity(1.0)
        self.update()
        self._animation_timer.start(30)

    def hide_hud(self) -> None:
        """Fade out the HUD by setting opacity to 0.0 and stopping animation."""
        self.setWindowOpacity(0.0)
        self._animation_timer.stop()
        self.update()

    def set_confidence(self, confidence: float | None) -> None:
        """Display the confidence percentage on the HUD, or clear it."""
        if confidence is None:
            self.confidence_label.setText("")
        else:
            self.confidence_label.setText(f"{confidence * 100:.0f}%")