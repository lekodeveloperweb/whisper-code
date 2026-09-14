from unittest.mock import MagicMock, patch


def test_inject_text_pastes_and_restores():
    from src.utils.text_injector import TextInjector

    with (
        patch("pyperclip.paste", return_value="old clipboard"),
        patch("pyperclip.copy") as mock_copy,
        patch("src.utils.text_injector.Controller") as mock_ctrl,
    ):
        keyboard = MagicMock()
        mock_ctrl.return_value = keyboard
        keyboard.pressed.return_value.__enter__ = MagicMock()
        keyboard.pressed.return_value.__exit__ = MagicMock()

        injector = TextInjector()
        injector.inject_text("hello world")

        # Verify copy was called for text and to restore old clipboard
        copy_calls = [c[0][0] for c in mock_copy.call_args_list]
        assert "hello world" in copy_calls
        assert "old clipboard" in copy_calls


def test_inject_text_empty_does_nothing():
    from src.utils.text_injector import TextInjector

    with patch("pyperclip.copy") as mock_copy:
        injector = TextInjector()
        injector.inject_text("")

        assert mock_copy.call_count == 0


def test_inject_text_single_char():
    from src.utils.text_injector import TextInjector

    with (
        patch("pyperclip.paste", return_value=""),
        patch("pyperclip.copy") as mock_copy,
        patch("src.utils.text_injector.Controller") as mock_ctrl,
    ):
        keyboard = MagicMock()
        mock_ctrl.return_value = keyboard
        keyboard.pressed.return_value.__enter__ = MagicMock()
        keyboard.pressed.return_value.__exit__ = MagicMock()

        injector = TextInjector()
        injector.inject_text("x")

        copy_calls = [c[0][0] for c in mock_copy.call_args_list]
        assert "x" in copy_calls


def test_inject_text_none_does_nothing():
    from src.utils.text_injector import TextInjector

    with patch("pyperclip.copy") as mock_copy:
        injector = TextInjector()
        injector.inject_text(None)

        assert mock_copy.call_count == 0


def test_inject_text_checks_accessibility():
    from src.utils.text_injector import TextInjector

    with (
        patch(
            "src.utils.text_injector.check_accessibility_permission",
            return_value=True,
        ),
        patch("pyperclip.paste", return_value="old clipboard"),
        patch("pyperclip.copy") as mock_copy,
        patch("src.utils.text_injector.Controller") as mock_ctrl,
    ):
        keyboard = MagicMock()
        mock_ctrl.return_value = keyboard
        keyboard.pressed.return_value.__enter__ = MagicMock()
        keyboard.pressed.return_value.__exit__ = MagicMock()

        injector = TextInjector()
        injector.inject_text("hello")

        copy_calls = [c[0][0] for c in mock_copy.call_args_list]
        assert "hello" in copy_calls
        assert "old clipboard" in copy_calls


def test_inject_text_fallback_when_no_permission():
    from src.utils.text_injector import TextInjector

    with (
        patch("src.utils.text_injector.check_accessibility_permission", return_value=False),
        patch("pyperclip.copy") as mock_copy,
        patch("src.utils.text_injector.open_accessibility_settings"),
    ):
        injector = TextInjector()
        injector.inject_text("fallback text")

        mock_copy.assert_called_with("fallback text")


def test_check_accessibility_permission_returns_true():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="true")

        from src.utils.text_injector import check_accessibility_permission

        result = check_accessibility_permission()
        assert result is True


def test_check_accessibility_permission_returns_false():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="false")

        from src.utils.text_injector import check_accessibility_permission

        result = check_accessibility_permission()
        assert result is False


def test_open_accessibility_settings_runs_osascript():
    with patch("subprocess.run") as mock_run:
        from src.utils.text_injector import open_accessibility_settings

        open_accessibility_settings()

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "open"
        assert "Privacy_Accessibility" in args[1]


def test_check_accessibility_permission_handles_exception():
    with patch("subprocess.run", side_effect=Exception("subprocess error")):
        from src.utils.text_injector import check_accessibility_permission

        result = check_accessibility_permission()
        assert result is False


def test_inject_via_ax_api_returns_false_on_non_macos():
    """AX API injection should return False when the API is unavailable."""
    from src.utils.ax_injector import inject_via_ax_api

    # On non-macOS or when Accessibility framework is unavailable,
    # the function should return False gracefully (never raise).
    result = inject_via_ax_api("test text")
    assert result is False


def test_inject_text_falls_back_to_keyboard_when_ax_fails():
    """When AX API injection fails, should fall back to clipboard+Cmd+V."""
    from src.utils.text_injector import TextInjector

    with (
        patch(
            "src.utils.text_injector.check_accessibility_permission",
            return_value=True,
        ),
        patch("pyperclip.paste", return_value="old clipboard"),
        patch("pyperclip.copy") as mock_copy,
        patch("src.utils.ax_injector.inject_via_ax_api", return_value=False),
        patch("src.utils.text_injector.Controller") as mock_ctrl,
    ):
        keyboard = MagicMock()
        mock_ctrl.return_value = keyboard
        keyboard.pressed.return_value.__enter__ = MagicMock()
        keyboard.pressed.return_value.__exit__ = MagicMock()

        injector = TextInjector()
        injector.inject_text("fallback text")

        # Should have called clipboard methods (fallback path)
        copy_calls = [c[0][0] for c in mock_copy.call_args_list]
        assert "fallback text" in copy_calls
        assert "old clipboard" in copy_calls


def test_inject_text_succeeds_via_ax_api_skips_clipboard():
    """When AX API injection succeeds, should skip clipboard+Cmd+V entirely."""
    from src.utils.text_injector import TextInjector

    with (
        patch(
            "src.utils.text_injector.check_accessibility_permission",
            return_value=True,
        ),
        patch("pyperclip.copy") as mock_copy,
        patch("pyperclip.paste", return_value=""),
        patch("src.utils.ax_injector.inject_via_ax_api", return_value=True) as mock_ax,
    ):
        injector = TextInjector()
        injector.inject_text("ax injected text")

        # AX API should have been called
        mock_ax.assert_called_once_with("ax injected text")

        # Clipboard should NOT have been touched (AX succeeded)
        assert mock_copy.call_count == 0
