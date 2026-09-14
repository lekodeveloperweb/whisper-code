from unittest.mock import MagicMock, patch

import pytest
from pynput import keyboard


@pytest.fixture
def mock_keyboard():
    with patch("src.core.hotkey_listener.keyboard") as mock:
        mock.Key.cmd = keyboard.Key.cmd
        mock.Key.cmd_l = keyboard.Key.cmd_l
        mock.Key.cmd_r = keyboard.Key.cmd_r
        mock.Key.ctrl = keyboard.Key.ctrl
        mock.Key.ctrl_l = keyboard.Key.ctrl_l
        mock.Key.ctrl_r = keyboard.Key.ctrl_r
        mock.Key.enter = keyboard.Key.enter
        yield mock


@pytest.fixture
def mock_listener():
    with patch("src.core.hotkey_listener.keyboard.Listener") as mock:
        instance = MagicMock()
        mock.return_value = instance
        yield instance


def test_init_sets_default_hotkey():
    from src.core.hotkey_listener import HotkeyListener

    hotkey = HotkeyListener()
    assert hotkey.hotkey_str == "Cmd+Ctrl+T"


def test_on_press_tracks_cmd_modifier(mock_keyboard):
    from src.core.hotkey_listener import HotkeyListener

    hotkey = HotkeyListener()
    hotkey._modifiers = set()

    hotkey._on_press(keyboard.Key.cmd)

    assert keyboard.Key.cmd in hotkey._modifiers


def test_on_press_tracks_ctrl_modifier(mock_keyboard):
    from src.core.hotkey_listener import HotkeyListener

    hotkey = HotkeyListener()
    hotkey._modifiers = set()

    hotkey._on_press(keyboard.Key.ctrl)

    assert keyboard.Key.ctrl in hotkey._modifiers


def test_on_press_emits_triggered_for_cmd_ctrl_t(mock_keyboard):
    from src.core.hotkey_listener import HotkeyListener

    hotkey = HotkeyListener()
    hotkey._modifiers = set()

    emit_count = [0]

    def emit():
        emit_count[0] += 1

    hotkey.triggered = MagicMock()
    hotkey.triggered.emit = emit

    hotkey._on_press(keyboard.Key.cmd)
    hotkey._on_press(keyboard.Key.ctrl)
    hotkey._on_press(type("MockChar", (), {"char": "t"})())

    assert emit_count[0] == 1


def test_on_press_does_not_emit_for_single_key(mock_keyboard):
    from src.core.hotkey_listener import HotkeyListener

    hotkey = HotkeyListener()
    hotkey._modifiers = set()

    emit_count = [0]

    def emit():
        emit_count[0] += 1

    hotkey.triggered = MagicMock()
    hotkey.triggered.emit = emit

    hotkey._on_press(keyboard.Key.cmd)
    hotkey._on_press(MagicMock(char="a"))

    assert emit_count[0] == 0


def test_on_press_emits_confirmed_for_enter(mock_keyboard):
    from src.core.hotkey_listener import HotkeyListener

    hotkey = HotkeyListener()

    emit_count = [0]

    def emit():
        emit_count[0] += 1

    hotkey.confirmed = MagicMock()
    hotkey.confirmed.emit = emit

    hotkey._on_press(keyboard.Key.enter)

    assert emit_count[0] == 1


def test_on_release_removes_modifier(mock_keyboard):
    from src.core.hotkey_listener import HotkeyListener

    hotkey = HotkeyListener()
    hotkey._modifiers = {keyboard.Key.cmd}

    hotkey._on_release(keyboard.Key.cmd)

    assert keyboard.Key.cmd not in hotkey._modifiers


def test_start_calls_listener_start(mock_listener):
    from src.core.hotkey_listener import HotkeyListener

    hotkey = HotkeyListener()
    hotkey.start()

    mock_listener.start.assert_called_once()


def test_stop_calls_listener_stop(mock_listener):
    from src.core.hotkey_listener import HotkeyListener

    hotkey = HotkeyListener()
    hotkey.stop()

    mock_listener.stop.assert_called_once()
