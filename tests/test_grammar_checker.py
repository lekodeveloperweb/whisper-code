from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture
def mock_requests():
    with patch("src.core.grammar_checker.requests") as mock:
        yield mock


@pytest.fixture
def app():
    q_app = QApplication.instance()
    if q_app is None:
        q_app = QApplication([])
    return q_app


@pytest.fixture
def mock_pyqt_signal():
    """Replace pyqtSignal with a working mock for signal-based tests."""

    class _MockSignal:
        def __init__(self):
            self._callbacks = []

        def connect(self, cb):
            self._callbacks.append(cb)

        def emit(self, *args):
            for cb in self._callbacks:
                cb(*args)

    with patch(
        "PySide6.QtCore.Signal",
        return_value=_MockSignal(),
    ):
        yield


def test_success_emits_corrected(mock_requests, app):
    from src.core.grammar_checker import GrammarChecker

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": "  Hello, world!  "}}]}
    mock_requests.post.return_value = mock_response

    checker = GrammarChecker("http://localhost:8080", "gemma4-e4b-8b")
    checker.set_text("uh um hello world")

    results = []
    checker.finished.connect(results.append)

    # Extract and test the core logic directly
    from src.core.grammar_checker import check_grammar

    check_grammar(
        api_endpoint="http://localhost:8080/v1/chat/completions",
        model_name="gemma4-e4b-8b",
        text="uh um hello world",
        finished_cb=results.append,
        error_cb=lambda _: None,
    )

    assert len(results) == 1


def test_quote_stripping(mock_requests, app):
    from src.core.grammar_checker import check_grammar

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": '"hello world"'}}]}
    mock_requests.post.return_value = mock_response

    results = []
    check_grammar(
        api_endpoint="http://localhost:8080/v1/chat/completions",
        model_name="gemma4-e4b-8b",
        text="test",
        finished_cb=results.append,
        error_cb=lambda _: None,
    )

    assert results[0] == "hello world"


def test_empty_text_emits_error(mock_requests, app):
    from src.core.grammar_checker import check_grammar

    errors = []
    check_grammar(
        api_endpoint="http://localhost:8080/v1/chat/completions",
        model_name="gemma4-e4b-8b",
        text="",
        finished_cb=lambda _: None,
        error_cb=errors.append,
    )

    assert len(errors) == 1
    assert "No text" in errors[0]


def test_api_error_emits_error(mock_requests, app):
    from src.core.grammar_checker import check_grammar

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_requests.post.return_value = mock_response

    errors = []
    check_grammar(
        api_endpoint="http://localhost:8080/v1/chat/completions",
        model_name="gemma4-e4b-8b",
        text="test",
        finished_cb=lambda _: None,
        error_cb=errors.append,
    )

    assert len(errors) == 1
    assert "400" in errors[0]


def test_payload_structure(mock_requests, app):
    from src.core.grammar_checker import check_grammar

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
    mock_requests.post.return_value = mock_response

    check_grammar(
        api_endpoint="http://localhost:8080/v1/chat/completions",
        model_name="gemma4-e4b-8b",
        text="test input",
        finished_cb=lambda _: None,
        error_cb=lambda _: None,
    )

    call_args = mock_requests.post.call_args
    payload = call_args[1]["json"]

    assert payload["model"] == "gemma4-e4b-8b"
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"
    assert payload["messages"][1]["content"] == "test input"
    assert payload["stream"] is False


class TestGrammarChecker:
    def test_grammarchecker_init_sets_endpoints(self, mock_pyqt_signal):
        from src.core.grammar_checker import GrammarChecker

        checker = GrammarChecker("http://localhost:8080", "gemma4-e4b-8b")
        assert checker.api_endpoint == "http://localhost:8080/v1/chat/completions"
        assert checker.model_name == "gemma4-e4b-8b"

    def test_grammarchecker_init_strips_trailing_slash(self, mock_pyqt_signal):
        from src.core.grammar_checker import GrammarChecker

        checker = GrammarChecker("http://localhost:8080/", "gemma4-e4b-8b")
        assert checker.api_endpoint == "http://localhost:8080/v1/chat/completions"

    def test_grammarchecker_set_text(self, mock_pyqt_signal):
        from src.core.grammar_checker import GrammarChecker

        checker = GrammarChecker("http://localhost:8080", "gemma4-e4b-8b")
        checker.set_text("text to fix")
        assert checker.text_to_fix == "text to fix"

    def test_grammarchecker_run_success_emits_finished(self, mock_pyqt_signal, mock_requests, app):
        from src.core.grammar_checker import GrammarChecker

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "corrected text"}}]}
        mock_requests.post.return_value = mock_response

        checker = GrammarChecker("http://localhost:8080", "gemma4-e4b-8b")
        checker.set_text("fix this")
        results = []
        checker.finished.connect(results.append)
        checker.run()

        assert len(results) == 1
        assert results[0] == "corrected text"

    def test_grammarchecker_run_error_emits_error(self, mock_pyqt_signal, mock_requests, app):
        from src.core.grammar_checker import GrammarChecker

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_requests.post.return_value = mock_response

        checker = GrammarChecker("http://localhost:8080", "gemma4-e4b-8b")
        checker.set_text("fix this")
        errors = []
        checker.error.connect(errors.append)
        checker.run()

        assert len(errors) == 1
        assert "500" in errors[0]

    def test_grammarchecker_run_system_prompt_included(self, mock_pyqt_signal, mock_requests, app):
        from src.core.grammar_checker import GrammarChecker

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        mock_requests.post.return_value = mock_response

        checker = GrammarChecker("http://localhost:8080", "gemma4-e4b-8b")
        checker.set_text("user text")
        checker.run()

        call_args = mock_requests.post.call_args
        payload = call_args[1]["json"]

        assert payload["messages"][0]["role"] == "system"
        assert "technical editor" in payload["messages"][0]["content"].lower()
        assert payload["messages"][1]["content"] == "user text"

    def test_grammarchecker_run_exception_emits_error(self, mock_pyqt_signal, mock_requests, app):
        import requests as req

        from src.core.grammar_checker import GrammarChecker

        mock_requests.post.side_effect = req.exceptions.ConnectionError("connection refused")

        checker = GrammarChecker("http://localhost:8080", "gemma4-e4b-8b")
        checker.set_text("fix this")
        errors = []
        checker.error.connect(errors.append)
        checker.run()

        assert len(errors) == 1
        assert "connection" in errors[0]
