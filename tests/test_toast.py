from unittest.mock import patch


def test_toast_error_runs_osascript():
    from src.utils.toast import ToastNotifier

    with (
        patch("src.utils.toast._is_macos", return_value=True),
        patch("subprocess.run") as mock_run,
    ):
        notifier = ToastNotifier()
        notifier.error("Something went wrong")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "Something went wrong" in cmd


def test_toast_info_runs_osascript():
    from src.utils.toast import ToastNotifier

    with (
        patch("src.utils.toast._is_macos", return_value=True),
        patch("subprocess.run") as mock_run,
    ):
        notifier = ToastNotifier()
        notifier.info("Dictation complete")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "Dictation complete" in cmd


def test_toast_error_has_red_color():
    from src.utils.toast import ToastNotifier

    with (
        patch("src.utils.toast._is_macos", return_value=True),
        patch("subprocess.run") as mock_run,
    ):
        notifier = ToastNotifier()
        notifier.error("Failed")
        cmd = mock_run.call_args[0][0]
        assert "FF0000" in cmd


def test_toast_info_has_white_color():
    from src.utils.toast import ToastNotifier

    with (
        patch("src.utils.toast._is_macos", return_value=True),
        patch("subprocess.run") as mock_run,
    ):
        notifier = ToastNotifier()
        notifier.info("Complete")
        cmd = mock_run.call_args[0][0]
        assert "FFFFFF" in cmd


def test_error_handler_calls_toast():
    from src.utils.toast import ToastNotifier

    with patch.object(ToastNotifier, "error") as mock_error:
        notifier = ToastNotifier()
        notifier.error("Test error")
        mock_error.assert_called_once_with("Test error")


def test_toast_notifies_on_non_macos():
    from src.utils.toast import ToastNotifier

    with (
        patch("src.utils.toast._is_macos", return_value=False),
        patch("subprocess.run") as mock_run,
    ):
        notifier = ToastNotifier()
        notifier.error("Should not run")
        mock_run.assert_not_called()


def test_toast_notify_builds_command():
    from src.utils.toast import ToastNotifier

    with (
        patch("src.utils.toast._is_macos", return_value=True),
        patch("subprocess.run") as mock_run,
    ):
        notifier = ToastNotifier()
        notifier.notify("Hello")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "osascript" in cmd
        assert "Hello" in cmd


def test_toast_notify_with_subtitle():
    from src.utils.toast import ToastNotifier

    with (
        patch("src.utils.toast._is_macos", return_value=True),
        patch("subprocess.run") as mock_run,
    ):
        notifier = ToastNotifier()
        notifier.notify("msg", app_name="MyApp", subtitle="sub")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "MyApp" in cmd


def test_is_macos_returns_true_on_darwin():
    with patch("platform.system", return_value="Darwin"):
        from src.utils.toast import _is_macos

        assert _is_macos() is True


def test_is_macos_returns_false_on_linux():
    with patch("platform.system", return_value="Linux"):
        from src.utils.toast import _is_macos

        assert _is_macos() is False


def test_toast_info_skips_on_non_macos():
    from src.utils.toast import ToastNotifier

    with (
        patch("src.utils.toast._is_macos", return_value=False),
        patch("subprocess.run") as mock_run,
    ):
        notifier = ToastNotifier()
        notifier.info("Should not run")
        mock_run.assert_not_called()


def test_toast_error_skips_on_non_macos():
    from src.utils.toast import ToastNotifier

    with (
        patch("src.utils.toast._is_macos", return_value=False),
        patch("subprocess.run") as mock_run,
    ):
        notifier = ToastNotifier()
        notifier.error("Should not run")
        mock_run.assert_not_called()
