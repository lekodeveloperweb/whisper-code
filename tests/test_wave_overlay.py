from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

OVERLAY_WIDTH = 440
OVERLAY_HEIGHT = 140
NORMALIZED_RMS = 0.5


def test_init_sets_window_flags(qapp):
    from src.gui.wave_overlay import WaveOverlay

    overlay = WaveOverlay()
    flags = overlay.windowFlags()
    assert flags & Qt.WindowType.ToolTip


def test_init_sets_translucent_background(qapp):
    from src.gui.wave_overlay import WaveOverlay

    overlay = WaveOverlay()
    assert overlay.testAttribute(Qt.WA_TranslucentBackground)


def test_init_sets_fixed_size(qapp):
    from src.gui.wave_overlay import WaveOverlay

    overlay = WaveOverlay()
    assert overlay.width() == OVERLAY_WIDTH
    assert overlay.height() == OVERLAY_HEIGHT


def test_init_sets_zero_opacity(qapp):
    from src.gui.wave_overlay import WaveOverlay

    overlay = WaveOverlay()
    assert overlay.windowOpacity() == 0.0


def test_init_creates_labels(qapp):
    from src.gui.wave_overlay import WaveOverlay

    overlay = WaveOverlay()
    assert isinstance(overlay.label, QLabel)
    assert isinstance(overlay.confidence_label, QLabel)


def test_set_rms_normalizes(qapp):
    from src.gui.wave_overlay import WaveOverlay

    overlay = WaveOverlay()
    overlay.set_rms(1000)
    assert overlay._rms == NORMALIZED_RMS


def test_set_rms_clamps_high(qapp):
    from src.gui.wave_overlay import WaveOverlay

    overlay = WaveOverlay()
    overlay.set_rms(5000)
    assert overlay._rms == 1.0


def test_show_hud_sets_opacity(qapp):
    from src.gui.wave_overlay import WaveOverlay

    overlay = WaveOverlay()
    overlay.setWindowOpacity(0.0)
    overlay.show_hud("Test")
    assert overlay.windowOpacity() == 1.0


def test_show_hud_sets_text(qapp):
    from src.gui.wave_overlay import WaveOverlay

    overlay = WaveOverlay()
    overlay.show_hud("Custom text")
    assert overlay.label.text() == "Custom text"


def test_hide_hud_stops_timer(qapp):
    from src.gui.wave_overlay import WaveOverlay

    overlay = WaveOverlay()
    overlay.show_hud()
    overlay._animation_timer.start(100)
    overlay.hide_hud()
    assert overlay._animation_timer.isActive() is False


def test_set_confidence_with_value(qapp):
    from src.gui.wave_overlay import WaveOverlay

    overlay = WaveOverlay()
    overlay.set_confidence(0.95)
    assert overlay.confidence_label.text() == "95%"


def test_set_confidence_with_none(qapp):
    from src.gui.wave_overlay import WaveOverlay

    overlay = WaveOverlay()
    overlay.set_confidence(None)
    assert overlay.confidence_label.text() == ""


def test_paint_event_draws_background(qapp):
    from src.gui.wave_overlay import WaveOverlay

    overlay = WaveOverlay()
    overlay.setWindowOpacity(1.0)
    overlay.show()

    from PySide6.QtGui import QPainter

    painter = QPainter(overlay)
    overlay.paintEvent(painter)
    painter.end()


def test_paint_event_draws_labels(qapp):
    from PySide6.QtGui import QPainter

    from src.gui.wave_overlay import WaveOverlay

    overlay = WaveOverlay()
    overlay.show_hud("paint test")

    painter = QPainter(overlay)
    overlay.paintEvent(painter)
    painter.end()

    assert overlay.label.text() == "paint test"