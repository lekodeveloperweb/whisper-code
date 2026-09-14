import contextlib
import os
import sys
import threading
from pathlib import Path
from unittest import mock

# Mock pynput.keyboard BEFORE any test modules are collected.
# On macOS, importing real pynput triggers accessibility permission dialogs.


def _make_listener_factory(*args, **kwargs):  # noqa: ARG003
    """Factory returning an inert pynput Listener stub.

    The stub runs no worker thread, so join() returns immediately —
    matching real pynput semantics for an already-stopped listener.
    The previous stub blocked forever on an internal Event, which left
    _HotkeyRecorder QThreads running at Qt module shutdown and aborted
    the process (qFatal -> SIGABRT), surfacing the macOS crash-report
    window during test runs.
    """

    class _StubListener:
        def __init__(self, *args2, **kwargs2):  # noqa: ARG003
            self._stop_event = threading.Event()

        def __enter__(self):  # noqa: ARG002
            return self

        def __exit__(self, *args):  # noqa: ARG002
            self._stop_event.set()

        def join(self, timeout=None):  # noqa: ARG001
            # Nothing is running, so join is a no-op (real pynput
            # returns immediately once the listener thread has exited).
            return True

        def stop(self):
            self._stop_event.set()

    return _StubListener(*args, **kwargs)


_keyboard_mock = mock.MagicMock(
    Key=mock.MagicMock(
        cmd=object(),
        cmd_l=object(),
        cmd_r=object(),
        ctrl=object(),
        ctrl_l=object(),
        ctrl_r=object(),
    ),
    Controller=mock.MagicMock,
)
_keyboard_mock.Listener = _make_listener_factory

_pynput_mock = mock.MagicMock()
_pynput_mock.keyboard = _keyboard_mock
sys.modules["pynput"] = _pynput_mock
# Register submodules so `from pynput.keyboard import X` resolves
sys.modules["pynput.keyboard"] = _keyboard_mock

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

_scripts_dir = Path(__file__).resolve().parent.parent / "scripts"  # noqa: E402
os.environ["QT_QPA_PLATFORM"] = "offscreen"  # noqa: E402

_all_dialogs: list[object] = []


def _keep_dialog(dialog: object) -> None:
    """Register a dialog to keep it alive until the next test.

    Also keeps SettingsDialog instances alive so their child C++ widgets
    (QLineEdit, QComboBox, etc.) are not prematurely deleted by Shiboken.
    """
    _all_dialogs.append(dialog)


def pytest_configure(config):
    """Inject scripts/ into sys.path before test collection."""
    if str(_scripts_dir) not in sys.path:
        sys.path.insert(0, str(_scripts_dir))


@pytest.fixture(scope="session", autouse=True)
def _qt_attrs():
    pass


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# Module-level list to keep all SettingsDialog instances alive across tests.
_all_settings_dialogs: list[object] = []

# Flag to ensure patching happens only once.
_settings_dialogs_patched = False


def _patch_settings_dialog():
    """Monkey-patch SettingsDialog.__init__ to auto-register instances."""
    global _settings_dialogs_patched  # noqa: PLW0603
    if _settings_dialogs_patched:
        return

    from src.gui.settings_dialog import SettingsDialog

    _original_init = SettingsDialog.__init__

    def _patched_init(self, *args, **kwargs):
        _original_init(self, *args, **kwargs)
        _all_settings_dialogs.append(self)

    SettingsDialog.__init__ = _patched_init
    _settings_dialogs_patched = True


@pytest.fixture(autouse=True)
def _keep_dialogs_alive():
    """Keep SettingsDialog instances alive across tests."""
    _patch_settings_dialog()


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point HOME at a temp dir and clear WHISPER_* env overrides.

    ConfigManager reads ~/.config/whisper-code/settings.json, so without
    isolation the suite only passes on machines whose personal config
    happens to match the asserted defaults (and stray WHISPER_* exports
    in the developer shell leak into env-override tests).
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    for key in list(os.environ):
        if key.startswith("WHISPER_"):
            monkeypatch.delenv(key)


# Module-level list of AudioRecorder instances started during a test.
_tracked_recorders: list[object] = []
_recorders_patched = False


def _patch_recorder_tracking():
    """Track every AudioRecorder that starts recording during a test.

    Tests that call start_recording() without stop_recording() leave a
    daemon capture thread busy-looping on a mocked stream for the rest
    of the session: it burns CPU and, by allocating constantly, can
    trigger Python's generational GC inside that thread — which then
    destroys timer-owning QObjects cross-thread (Qt fatal
    "Timers cannot be stopped from another thread" warnings, and aborts
    during PySide teardown).
    """
    global _recorders_patched  # noqa: PLW0603
    if _recorders_patched:
        return

    from src.core.audio_recorder import AudioRecorder

    original_start = AudioRecorder.start_recording

    def _tracked_start(self: AudioRecorder) -> None:
        _tracked_recorders.append(self)
        original_start(self)

    AudioRecorder.start_recording = _tracked_start  # type: ignore[method-assign]
    _recorders_patched = True


@pytest.fixture(autouse=True)
def _stop_leaked_recorders():
    """Stop any recorder still capturing when the test ends."""
    _patch_recorder_tracking()
    yield
    for recorder in _tracked_recorders:
        stop = getattr(recorder, "stop_recording", None)
        if callable(stop):
            with contextlib.suppress(Exception):
                stop()
    _tracked_recorders.clear()


@pytest.fixture(autouse=True)
def _cleanup_qt_objects():
    """Drop kept Qt objects after each test, in the main thread.

    PySide deletes every surviving Shiboken-wrapped QObject at Qt module
    shutdown; destroying a still-running QThread there calls qFatal() and
    aborts the process (native macOS crash-report window). Clearing the
    keeper lists here lets refcounting collect the dialogs mid-session.
    """
    yield
    _all_dialogs.clear()
    _all_settings_dialogs.clear()
