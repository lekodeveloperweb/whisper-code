from unittest.mock import patch

_EXIT_CODE: int = 42


def test_main_entry_point_calls_main():
    with patch("src.whisper_code.cli.main") as mock_main:
        mock_main.return_value = 0

        from src.whisper_code.cli import main

        main()

        mock_main.assert_called_once()


def test_main_return_value():
    with patch("src.whisper_code.cli.main") as mock_main:
        mock_main.return_value = _EXIT_CODE

        from src.whisper_code.cli import main

        result = main()

        assert result == _EXIT_CODE


def test_main_module_import():
    from src.whisper_code import __main__

    assert hasattr(__main__, "main")
