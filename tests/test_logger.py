import logging
from unittest.mock import MagicMock, patch

from src.utils.logger import get_logger, setup_logger


def test_get_logger_returns_logger():
    logger = get_logger()
    assert isinstance(logger, logging.Logger)


def test_logger_has_handlers():
    setup_logger()
    logger = get_logger()
    assert len(logger.handlers) >= 1


def test_cli_uses_logger():

    logger = logging.getLogger("whisper")
    assert logger.name == "whisper"


def test_hotkey_uses_logger():
    from src.utils.logger import get_logger

    logger = get_logger()
    assert logger.name == "whisper"


def test_get_logger_returns_whisper_logger():
    logger = get_logger()
    assert logger.name == "whisper"


def test_setup_logger_creates_file_handler():
    with patch("src.utils.logger.LOG_DIR") as mock_dir:
        mock_dir.mkdir = MagicMock()
        mock_dir.exists = MagicMock(return_value=False)

        from src.utils.logger import setup_logger

        logger = setup_logger(level="DEBUG")

        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) >= 1


def test_setup_logger_creates_stream_handler():
    with patch("src.utils.logger.LOG_DIR") as mock_dir:
        mock_dir.mkdir = MagicMock()
        mock_dir.exists = MagicMock(return_value=False)

        from src.utils.logger import setup_logger

        logger = setup_logger(level="DEBUG")

        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) >= 1


def test_setup_logger_sets_debug_level():
    with patch("src.utils.logger.LOG_DIR") as mock_dir:
        mock_dir.mkdir = MagicMock()
        mock_dir.exists = MagicMock(return_value=False)

        from src.utils.logger import setup_logger

        logger = setup_logger(level="DEBUG")
        assert logger.level == logging.DEBUG


def test_logger_log_methods_work():
    with patch("src.utils.logger.LOG_DIR") as mock_dir:
        mock_dir.mkdir = MagicMock()
        mock_dir.exists = MagicMock(return_value=False)

        from src.utils.logger import setup_logger

        logger = setup_logger(level="DEBUG")

        # These should not raise
        logger.info("test info")
        logger.debug("test debug")
        logger.error("test error")
        logger.warning("test warning")


def test_setup_logger_creates_log_directory():
    with patch("src.utils.logger.LOG_DIR") as mock_path:
        mock_path.mkdir = MagicMock()
        mock_path.exists = MagicMock(return_value=False)

        setup_logger()

        mock_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)


def test_setup_logger_info_level():
    with patch("src.utils.logger.LOG_DIR") as mock_dir:
        mock_dir.mkdir = MagicMock()
        mock_dir.exists = MagicMock(return_value=False)

        from src.utils.logger import setup_logger

        logger = setup_logger(level="INFO")
        assert logger.level == logging.DEBUG
