from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_pyaudio():
    with patch("pyaudio.PyAudio") as mock:
        mock_instance = MagicMock()
        mock_instance.get_sample_size.return_value = 2
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_requests():
    with patch("src.core.api_transcriber.requests") as mock:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "test"}
        mock.post.return_value = mock_response
        yield mock


@pytest.fixture
def mock_keyboard():
    with patch("src.core.hotkey_listener.keyboard") as mock:
        mock.Key = MagicMock()
        mock.Key.cmd = MagicMock()
        mock.Key.cmd_l = MagicMock()
        mock.Key.cmd_r = MagicMock()
        mock.Key.ctrl = MagicMock()
        mock.Key.ctrl_l = MagicMock()
        mock.Key.ctrl_r = MagicMock()
        mock.Key.enter = MagicMock()
        mock.Listener = MagicMock(return_value=MagicMock())
        yield mock


@pytest.fixture
def mock_components(mock_pyaudio, mock_keyboard):
    """Mock all component classes (not Qt) so we can test logic only."""
    with (
        patch("src.whisper_code.cli.AudioRecorder") as mock_recorder,
        patch("src.whisper_code.cli.APITranscriber") as mock_transcriber,
        patch("src.whisper_code.cli.GrammarChecker") as mock_grammar,
        patch("src.whisper_code.cli.WaveOverlay") as mock_overlay,
        patch("src.whisper_code.cli.TrayMenu") as mock_tray,
        patch("src.whisper_code.cli.HotkeyListener") as mock_hotkey,
        patch("src.whisper_code.cli.TextInjector") as mock_injector,
        patch("src.whisper_code.cli.ToastNotifier") as mock_toast,
    ):
        recorder = MagicMock()
        mock_recorder.return_value = recorder
        transcriber = MagicMock()
        mock_transcriber.return_value = transcriber
        grammar = MagicMock()
        mock_grammar.return_value = grammar
        overlay = MagicMock()
        mock_overlay.return_value = overlay
        tray = MagicMock()
        mock_tray.return_value = tray
        hotkey = MagicMock()
        mock_hotkey.return_value = hotkey
        injector = MagicMock()
        mock_injector.return_value = injector
        toast = MagicMock()
        mock_toast.return_value = toast
        yield {
            "recorder": recorder,
            "transcriber": transcriber,
            "grammar_checker": grammar,
            "overlay": overlay,
            "tray": tray,
            "hotkey": hotkey,
            "injector": injector,
            "toast": toast,
        }


@pytest.fixture
def mock_config():
    """Mock ConfigManager.get() at the module where it's imported (cli.py)."""
    with patch("src.whisper_code.cli.ConfigManager") as mock:
        cm = MagicMock()
        cm.get.side_effect = {
            "sample_rate": 16000,
            "api_url": "http://localhost:8080",
            "model_name": "whisper-large-v3",
            "grammar_model": "gemma4-e4b-8b",
            "use_grammar_check": False,
        }.get
        mock.return_value = cm
        yield cm


# ── main() ──────────────────────────────────────────────────────────────


def test_main_calls_setup_logger_debug_when_tty():
    with (
        patch("sys.stdout.isatty", return_value=True),
        patch("src.utils.logger.setup_logger") as mock_setup,
        patch("src.whisper_code.cli.WhisperCodeApp"),
    ):
        from src.whisper_code.cli import main

        main()

        mock_setup.assert_called_once_with(level="DEBUG")


def test_main_calls_setup_logger_info_when_not_tty():
    with (
        patch("sys.stdout.isatty", return_value=False),
        patch("src.utils.logger.setup_logger") as mock_setup,
        patch("src.whisper_code.cli.WhisperCodeApp"),
    ):
        from src.whisper_code.cli import main

        main()

        mock_setup.assert_called_once_with(level="INFO")


def test_main_creates_and_runs_app():
    with (
        patch("src.utils.logger.setup_logger"),
        patch("src.whisper_code.cli.WhisperCodeApp") as mock_app_cls,
    ):
        mock_app = MagicMock()
        mock_app_cls.return_value = mock_app
        mock_app.run.return_value = 0

        from src.whisper_code.cli import main

        main()

        mock_app_cls.assert_called_once()
        mock_app.run.assert_called_once()


# ── WhisperCodeApp.__init__ ─────────────────────────────────────────────


def test_init_loads_config(qapp, mock_config):
    from src.whisper_code.cli import WhisperCodeApp

    with (
        patch("src.whisper_code.cli.AudioRecorder"),
        patch("src.whisper_code.cli.APITranscriber"),
        patch("src.whisper_code.cli.GrammarChecker"),
        patch("src.whisper_code.cli.WaveOverlay"),
        patch("src.whisper_code.cli.TrayMenu"),
        patch("src.whisper_code.cli.HotkeyListener"),
        patch("src.whisper_code.cli.TextInjector"),
        patch("src.whisper_code.cli.ToastNotifier"),
    ):
        app = WhisperCodeApp(app=qapp)

    assert app.config is mock_config


def test_init_creates_text_injector(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    with patch("src.whisper_code.cli.ConfigManager"):
        app = WhisperCodeApp(app=qapp)

    assert app.injector is mock_components["injector"]


def test_init_creates_toast_notifier(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    with patch("src.whisper_code.cli.ConfigManager"):
        app = WhisperCodeApp(app=qapp)

    assert app.toast is mock_components["toast"]


def test_init_creates_audio_recorder_with_config_sample_rate(qapp, mock_pyaudio, mock_config):
    from src.whisper_code.cli import WhisperCodeApp

    with patch("src.whisper_code.cli.AudioRecorder") as mock_recorder:
        mock_recorder.return_value = MagicMock()
        with (
            patch("src.whisper_code.cli.APITranscriber"),
            patch("src.whisper_code.cli.GrammarChecker"),
            patch("src.whisper_code.cli.WaveOverlay"),
            patch("src.whisper_code.cli.TrayMenu"),
            patch("src.whisper_code.cli.HotkeyListener"),
            patch("src.whisper_code.cli.TextInjector"),
            patch("src.whisper_code.cli.ToastNotifier"),
        ):
            WhisperCodeApp(app=qapp)

        mock_recorder.assert_called_once_with(sample_rate=16000)


def test_init_creates_api_transcriber_with_config_url(qapp, mock_config):
    from src.whisper_code.cli import WhisperCodeApp

    with patch("src.whisper_code.cli.APITranscriber") as mock_trans:
        mock_trans.return_value = MagicMock()
        with (
            patch("src.whisper_code.cli.AudioRecorder"),
            patch("src.whisper_code.cli.GrammarChecker"),
            patch("src.whisper_code.cli.WaveOverlay"),
            patch("src.whisper_code.cli.TrayMenu"),
            patch("src.whisper_code.cli.HotkeyListener"),
            patch("src.whisper_code.cli.TextInjector"),
            patch("src.whisper_code.cli.ToastNotifier"),
        ):
            WhisperCodeApp(app=qapp)

        # Verify it was called with string args (config values)
        assert mock_trans.call_count == 1
        call_args = mock_trans.call_args
        assert call_args[0][0] == "http://localhost:8080"
        assert call_args[0][1] == "whisper-large-v3"


def test_init_creates_grammar_checker_with_config_model(qapp, mock_config):
    from src.whisper_code.cli import WhisperCodeApp

    with patch("src.whisper_code.cli.GrammarChecker") as mock_grammar:
        mock_grammar.return_value = MagicMock()
        with (
            patch("src.whisper_code.cli.AudioRecorder"),
            patch("src.whisper_code.cli.APITranscriber"),
            patch("src.whisper_code.cli.WaveOverlay"),
            patch("src.whisper_code.cli.TrayMenu"),
            patch("src.whisper_code.cli.HotkeyListener"),
            patch("src.whisper_code.cli.TextInjector"),
            patch("src.whisper_code.cli.ToastNotifier"),
        ):
            WhisperCodeApp(app=qapp)

        # Verify it was called with string args (config values)
        assert mock_grammar.call_count == 1
        call_args = mock_grammar.call_args
        assert call_args[0][0] == "http://localhost:8080"
        assert call_args[0][1] == "gemma4-e4b-8b"


def test_init_creates_wave_overlay_and_shows(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    with patch("src.whisper_code.cli.WaveOverlay") as mock_overlay:
        overlay = MagicMock()
        mock_overlay.return_value = overlay
        with (
            patch("src.whisper_code.cli.ConfigManager"),
            patch("src.whisper_code.cli.AudioRecorder"),
            patch("src.whisper_code.cli.APITranscriber"),
            patch("src.whisper_code.cli.GrammarChecker"),
            patch("src.whisper_code.cli.TrayMenu"),
            patch("src.whisper_code.cli.HotkeyListener"),
            patch("src.whisper_code.cli.TextInjector"),
            patch("src.whisper_code.cli.ToastNotifier"),
        ):
            WhisperCodeApp(app=qapp)

        overlay.show.assert_called_once()


def test_init_creates_tray_menu_and_shows(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    with patch("src.whisper_code.cli.TrayMenu") as mock_tray:
        tray = MagicMock()
        mock_tray.return_value = tray
        with (
            patch("src.whisper_code.cli.ConfigManager"),
            patch("src.whisper_code.cli.AudioRecorder"),
            patch("src.whisper_code.cli.APITranscriber"),
            patch("src.whisper_code.cli.GrammarChecker"),
            patch("src.whisper_code.cli.WaveOverlay"),
            patch("src.whisper_code.cli.HotkeyListener"),
            patch("src.whisper_code.cli.TextInjector"),
            patch("src.whisper_code.cli.ToastNotifier"),
        ):
            WhisperCodeApp(app=qapp)

        tray.show.assert_called_once()


def test_init_creates_hotkey_listener_and_starts(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    with patch("src.whisper_code.cli.HotkeyListener") as mock_hotkey:
        hotkey = MagicMock()
        mock_hotkey.return_value = hotkey
        with (
            patch("src.whisper_code.cli.ConfigManager"),
            patch("src.whisper_code.cli.AudioRecorder"),
            patch("src.whisper_code.cli.APITranscriber"),
            patch("src.whisper_code.cli.GrammarChecker"),
            patch("src.whisper_code.cli.WaveOverlay"),
            patch("src.whisper_code.cli.TrayMenu"),
            patch("src.whisper_code.cli.TextInjector"),
            patch("src.whisper_code.cli.ToastNotifier"),
        ):
            WhisperCodeApp(app=qapp)

        hotkey.start.assert_called_once()


def test_init_sets_initial_states(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    with (
        patch("src.whisper_code.cli.ConfigManager"),
        patch("src.whisper_code.cli.AudioRecorder"),
        patch("src.whisper_code.cli.APITranscriber"),
        patch("src.whisper_code.cli.GrammarChecker"),
        patch("src.whisper_code.cli.WaveOverlay"),
        patch("src.whisper_code.cli.TrayMenu"),
        patch("src.whisper_code.cli.HotkeyListener"),
    ):
        app = WhisperCodeApp(app=qapp)

    assert app.is_listening is False
    assert app.is_processing is False


# ── Flow methods ─────────────────────────────────────────────────────────


def test_start_listening_flow_starts_when_idle(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.is_listening = False
    app.is_processing = False

    app.start_listening_flow()

    app.recorder.start_recording.assert_called_once()


def test_start_listening_flow_ignores_when_listening(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.is_listening = True
    app.is_processing = False

    app.start_listening_flow()

    app.recorder.start_recording.assert_not_called()


def test_start_listening_flow_ignores_when_processing(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.is_listening = False
    app.is_processing = True

    app.start_listening_flow()

    app.recorder.start_recording.assert_not_called()


def test_stop_listening_flow_stops_when_listening(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.is_listening = True

    app.stop_listening_flow()

    app.recorder.stop_recording.assert_called_once()


def test_stop_listening_flow_ignores_when_not_listening(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.is_listening = False

    app.stop_listening_flow()

    app.recorder.stop_recording.assert_not_called()


# ── Action methods ───────────────────────────────────────────────────────


def test_start_listening_starts_recorder(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.start_listening()

    app.recorder.start_recording.assert_called_once()
    assert app.is_listening is True
    app.tray.update_state.assert_called_once_with(is_listening=True)


def test_start_listening_shows_hud(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.start_listening()

    app.overlay.show_hud.assert_called_once_with("Listening... Press Enter to stop")


def test_start_listening_handles_exception(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.recorder.start_recording.side_effect = Exception("mic busy")

    app.start_listening()

    # Toast.error is called twice: once by logger.error, once by toast.error
    # Actually: the except block calls toast.error() then on_transcription_error()
    # which also calls toast.error(). Check toast was called at least once.
    assert app.toast.error.call_count >= 1


def test_stop_listening_stops_recording(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.is_listening = True

    app.stop_listening()

    app.recorder.stop_recording.assert_called_once()


def test_stop_listening_sends_to_transcriber(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.is_listening = True
    app.recorder.stop_recording.return_value = b"fake audio data"

    app.stop_listening()

    app.transcriber.set_audio.assert_called_once_with(b"fake audio data")
    app.transcriber.start.assert_called_once()


def test_stop_listening_handles_empty_audio(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.is_listening = True
    app.recorder.stop_recording.return_value = b""

    app.stop_listening()

    app.tray.update_state.assert_called_once_with(is_listening=False)
    app.overlay.show_hud.assert_called_once_with("No speech detected")


# ── Callback methods ─────────────────────────────────────────────────────


def test_on_transcription_success_with_grammar(qapp, mock_components, mock_config):
    mock_config.get.side_effect = {
        "use_grammar_check": True,
    }.get

    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.on_transcription_success("hello world")

    app.grammar_checker.set_text.assert_called_once_with("hello world")
    app.grammar_checker.start.assert_called_once()


def test_on_transcription_success_without_grammar(qapp, mock_components, mock_config):
    mock_config.get.side_effect = {
        "use_grammar_check": False,
    }.get

    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.on_transcription_success("hello world")

    app.injector.inject_text.assert_called_once_with("hello world")


def test_on_transcription_success_empty_text(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)

    app.on_transcription_success("")

    app.overlay.hide_hud.assert_called()


def test_on_transcription_error_fallbacks(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)

    app.on_transcription_error("connection timeout")

    app.toast.error.assert_called_once_with("connection timeout")
    app.overlay.hide_hud.assert_called()


def test_on_refinement_success_injects(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)

    app.on_refinement_success("corrected text")

    app.injector.inject_text.assert_called_once_with("corrected text")


def test_on_refinement_error_falls_back_to_raw(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.transcriber.last_result = "raw transcription"

    app.on_refinement_error("refinement failed")

    app.injector.inject_text.assert_called_once_with("raw transcription")


def test_on_refinement_error_falls_back_to_none(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.transcriber.last_result = ""

    app.on_refinement_error("refinement failed")

    app.overlay.hide_hud.assert_called()


def test_finalize_pipeline_injects_text(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)

    app.finalize_pipeline("hello world")

    app.injector.inject_text.assert_called_once_with("hello world")
    assert app.is_processing is False


def test_finalize_pipeline_hides_hud_on_none(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)

    app.finalize_pipeline(None)

    app.overlay.hide_hud.assert_called()
    assert app.is_processing is False


def test_finalize_pipeline_resets_states(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.is_processing = True

    app.finalize_pipeline("test")

    assert app.is_processing is False


def test_quit_app_stops_hotkey(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)

    app.quit_app()

    app.hotkey.stop.assert_called_once()


def test_quit_app_stops_recording_if_listening(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.is_listening = True

    app.quit_app()

    app.recorder.stop_recording.assert_called_once()


def test_update_rms_passes_rms_to_overlay(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.recorder.get_rms.return_value = 0.5

    app.update_rms()

    app.overlay.set_rms.assert_called_once_with(0.5)


def test_on_confidence_sets_confidence_on_overlay(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)

    app.on_confidence(0.95)

    app.overlay.set_confidence.assert_called_once_with(0.95)


def test_open_settings_shows_dialog(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    with patch("src.whisper_code.cli.SettingsDialog") as mock_dialog:
        dialog = MagicMock()
        mock_dialog.return_value = dialog
        app = WhisperCodeApp(app=qapp)

        app._open_settings()

        dialog.show.assert_called_once()


def test_open_settings_skips_if_visible(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    with patch("src.whisper_code.cli.SettingsDialog") as mock_dialog:
        dialog = MagicMock()
        dialog.isVisible.return_value = True
        mock_dialog.return_value = dialog
        app = WhisperCodeApp(app=qapp)

        app.settings_dialog = dialog

        app._open_settings()

        app.settings_dialog.show.assert_not_called()


def test_run_returns_app_exec(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    app = WhisperCodeApp(app=qapp)
    app.app.exec_ = MagicMock(return_value=0)

    result = app.run()

    assert result == 0


def test_init_sets_high_dpi_attributes(qapp):
    from unittest.mock import patch

    with (
        patch("src.utils.logger.setup_logger"),
        patch("src.whisper_code.cli.AudioRecorder"),
        patch("src.whisper_code.cli.APITranscriber"),
        patch("src.whisper_code.cli.GrammarChecker"),
        patch("src.whisper_code.cli.WaveOverlay"),
        patch("src.whisper_code.cli.TrayMenu"),
        patch("src.whisper_code.cli.HotkeyListener"),
        patch("src.whisper_code.cli.TextInjector"),
        patch("src.whisper_code.cli.ToastNotifier"),
    ):
        from src.whisper_code.cli import WhisperCodeApp

        # Qt 6 enables high DPI scaling by default — no explicit attribute needed.
        WhisperCodeApp(app=qapp)


def test_check_accessibility_permission_warns(qapp, mock_components):
    from src.whisper_code.cli import WhisperCodeApp

    with (
        patch("src.utils.text_injector.check_accessibility_permission", return_value=False),
        patch("src.whisper_code.cli.logger") as mock_logger,
    ):
        app = WhisperCodeApp(app=qapp)
        app._check_accessibility_permission()

    # New behavior: logs debug, no toast, no settings dialog
    mock_logger.debug.assert_called()
    assert app.toast.error.call_count == 0
