from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu


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
