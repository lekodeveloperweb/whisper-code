from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QIcon
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class _PopupSpy:
    """Record QMenu.popup() calls without opening a native menu."""

    def __init__(self) -> None:
        self.calls: list[QPoint] = []

    def __call__(self, pos: QPoint, *args: object) -> QPoint:
        self.calls.append(pos)
        return pos


def _spy(tray: object) -> _PopupSpy:
    spy = _PopupSpy()
    tray.menu.popup = spy  # type: ignore[attr-defined]
    return spy


def test_init_creates_menu(qapp):
    from src.gui.tray_menu import TrayMenu

    tray = TrayMenu(lambda: None, lambda: None, lambda: None)
    assert isinstance(tray.menu, QMenu)


def test_init_adds_start_action(qapp):
    from src.gui.tray_menu import TrayMenu

    tray = TrayMenu(lambda: None, lambda: None, lambda: None)
    assert tray.start_action.text().startswith("Start Dictation")
    assert tray.start_action.isVisible()


def test_init_adds_stop_action_hidden(qapp):
    from src.gui.tray_menu import TrayMenu

    tray = TrayMenu(lambda: None, lambda: None, lambda: None)
    assert tray.stop_action.text().startswith("Stop Dictation")
    assert not tray.stop_action.isVisible()


def test_init_adds_quit_action(qapp):
    from src.gui.tray_menu import TrayMenu

    tray = TrayMenu(lambda: None, lambda: None, lambda: None)
    actions = tray.menu.actions()
    quit_action = None
    for a in actions:
        if a.text() == "Quit":
            quit_action = a
            break
    assert quit_action is not None


def test_init_sets_tooltip(qapp):
    from src.gui.tray_menu import TrayMenu

    tray = TrayMenu(lambda: None, lambda: None, lambda: None)
    assert tray.toolTip() == "Whisper-Code"


def test_create_microphone_icon_returns_icon(qapp):
    from src.gui.tray_menu import TrayMenu

    tray = TrayMenu(lambda: None, lambda: None, lambda: None)
    icon = tray._create_microphone_icon()
    assert isinstance(icon, QIcon)


def test_update_state_idle(qapp):
    from src.gui.tray_menu import TrayMenu

    tray = TrayMenu(lambda: None, lambda: None, lambda: None)
    tray.update_state(is_listening=False, is_processing=False)
    assert tray.start_action.isVisible()
    assert not tray.stop_action.isVisible()
    assert "Idle" in tray.toolTip()


def test_update_state_listening(qapp):
    from src.gui.tray_menu import TrayMenu

    tray = TrayMenu(lambda: None, lambda: None, lambda: None)
    tray.update_state(is_listening=True, is_processing=False)
    assert not tray.start_action.isVisible()
    assert tray.stop_action.isVisible()
    assert "Listening" in tray.toolTip()


def test_update_state_processing(qapp):
    from src.gui.tray_menu import TrayMenu

    tray = TrayMenu(lambda: None, lambda: None, lambda: None)
    tray.update_state(is_listening=False, is_processing=True)
    assert not tray.start_action.isVisible()
    assert not tray.stop_action.isVisible()
    assert "Transcribing" in tray.toolTip()


def test_settings_action_exists(qapp):
    from src.gui.tray_menu import TrayMenu

    tray = TrayMenu(lambda: None, lambda: None, lambda: None, lambda: None)
    assert tray.settings_action is not None
    assert "Settings" in tray.settings_action.text()


def test_tray_does_not_attach_qt_status_item_context_menu(qapp):
    """Regression: Qt's own status-item menu crashes the app on macOS.

    ``setContextMenu()`` makes libqcocoa's ``QStatusItemDelegate`` observe the
    NSStatusItem menu's begin-tracking notification, and that handler calls
    ``-[NSEvent clickCount]`` on ``[NSApp currentEvent]``. ``clickCount`` is
    only legal for mouse event types, so when a system-defined event is
    current (Fn/Globe or media-key events, which pynput's global tap keeps in
    the same Cocoa stream) AppKit raises
    ``NSInternalInconsistencyException: Invalid message sent to event
    "NSEvent: type=SysDefined ..."`` and the process aborts.

    Keeping the menu off the tray icon means Qt never installs that observer;
    the menu is popped ourselves from the ``activated`` signal instead.
    """
    from src.gui.tray_menu import TrayMenu

    tray = TrayMenu(lambda: None, lambda: None, lambda: None, lambda: None)
    assert tray.contextMenu() is None


def test_activation_reasons_show_menu_below_icon(qapp):
    """Left click, double click and right click all pop the menu."""
    from src.gui.tray_menu import TrayMenu

    reasons = [
        QSystemTrayIcon.ActivationReason.Trigger,
        QSystemTrayIcon.ActivationReason.DoubleClick,
        QSystemTrayIcon.ActivationReason.Context,
    ]
    for reason in reasons:
        tray = TrayMenu(lambda: None, lambda: None, lambda: None, lambda: None)
        tray.geometry = lambda: QRect(1200, 0, 24, 24)  # type: ignore[method-assign]
        spy = _spy(tray)

        tray._on_activated(reason)
        QTest.qWait(20)

        assert spy.calls == [QPoint(1200, 24)], f"reason {reason}"


def test_popup_is_deferred_outside_the_activation_event(qapp):
    """The menu must not pop up while the activating event is still current.

    Popping synchronously from the ``activated`` callback leaves whatever
    ``[NSApp currentEvent]`` AppKit was processing (possibly a system-defined
    event) as the current event for the menu tracking session, which is the
    condition that aborts the process.
    """
    from src.gui.tray_menu import TrayMenu

    tray = TrayMenu(lambda: None, lambda: None, lambda: None, lambda: None)
    tray.geometry = lambda: QRect(1200, 0, 24, 24)  # type: ignore[method-assign]
    spy = _spy(tray)

    tray._on_activated(QSystemTrayIcon.ActivationReason.Trigger)
    assert spy.calls == [], "menu popped synchronously inside the activation event"

    QTest.qWait(20)
    assert spy.calls == [QPoint(1200, 24)]


def test_unhandled_activation_reasons_do_not_show_menu(qapp):
    """Unknown/MiddleClick must not pop the menu."""
    from src.gui.tray_menu import TrayMenu

    reasons = [
        QSystemTrayIcon.ActivationReason.Unknown,
        QSystemTrayIcon.ActivationReason.MiddleClick,
    ]
    for reason in reasons:
        tray = TrayMenu(lambda: None, lambda: None, lambda: None, lambda: None)
        tray.geometry = lambda: QRect(1200, 0, 24, 24)  # type: ignore[method-assign]
        spy = _spy(tray)

        tray._on_activated(reason)
        QTest.qWait(20)

        assert spy.calls == [], f"reason {reason}"


def test_missing_geometry_falls_back_to_cursor(qapp):
    """A null tray geometry must not pop the menu at 0,0 over the desktop."""
    from src.gui.tray_menu import TrayMenu

    tray = TrayMenu(lambda: None, lambda: None, lambda: None, lambda: None)

    def _null_geometry() -> QRect:
        return QRect()

    tray.geometry = _null_geometry  # type: ignore[method-assign]
    spy = _spy(tray)

    tray._show_menu()

    assert len(spy.calls) == 1
    assert spy.calls[0] != QPoint(0, 0)
