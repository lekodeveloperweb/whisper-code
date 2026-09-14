from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

HIGH_CONFIDENCE = 0.95


@pytest.fixture
def mock_requests():
    with patch("src.core.api_transcriber.requests") as mock:
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


def test_success_emits_finished(mock_requests, app):
    from src.core.api_transcriber import transcribe

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "hello world"}
    mock_requests.post.return_value = mock_response

    results = []
    result = transcribe(
        api_endpoint="http://localhost:8080/v1/audio/transcriptions",
        model_name="whisper-large-v3",
        audio_data=b"fake wav",
        finished_cb=results.append,
    )

    assert len(results) == 1
    assert results[0] == "hello world"
    assert result == "hello world"
    mock_requests.post.assert_called_once()


def test_api_error_emits_error_signal(mock_requests, app):
    from src.core.api_transcriber import transcribe

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_requests.post.return_value = mock_response

    errors = []
    result = transcribe(
        api_endpoint="http://localhost:8080/v1/audio/transcriptions",
        model_name="whisper-large-v3",
        audio_data=b"fake wav",
        error_cb=errors.append,
    )

    assert len(errors) == 1
    assert "500" in errors[0]
    assert result is None


def test_connection_error_emits_error(mock_requests, app):
    import requests as req

    from src.core.api_transcriber import transcribe

    mock_requests.post.side_effect = req.exceptions.ConnectionError(" refused")

    errors = []
    result = transcribe(
        api_endpoint="http://localhost:9999/v1/audio/transcriptions",
        model_name="whisper-large-v3",
        audio_data=b"fake wav",
        error_cb=errors.append,
    )

    assert len(errors) == 1
    assert "Connection" in errors[0]
    assert result is None


def test_empty_audio_emits_error(mock_requests, app):
    from src.core.api_transcriber import transcribe

    errors = []
    result = transcribe(
        api_endpoint="http://localhost:8080/v1/audio/transcriptions",
        model_name="whisper-large-v3",
        audio_data=None,
        error_cb=errors.append,
    )

    assert len(errors) == 1
    assert "No audio" in errors[0]
    assert result is None


def test_confidence_emitted(mock_requests, app):
    from src.core.api_transcriber import transcribe

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "text": "hello",
        "confidence": 0.95,
    }
    mock_requests.post.return_value = mock_response

    confidences = []
    result = transcribe(
        api_endpoint="http://localhost:8080/v1/audio/transcriptions",
        model_name="whisper-large-v3",
        audio_data=b"fake wav",
        finished_cb=lambda _: None,
        confidence_cb=confidences.append,
    )

    assert len(confidences) == 1
    assert confidences[0] == HIGH_CONFIDENCE
    assert result == "hello"


class TestAPITranscriber:
    def test_apitranscriber_init_sets_urls(self, mock_pyqt_signal):
        from src.core.api_transcriber import APITranscriber

        transcriber = APITranscriber("http://localhost:8080", "whisper-large-v3")
        assert transcriber.base_url == "http://localhost:8080"
        assert transcriber.api_endpoint == "http://localhost:8080/v1/audio/transcriptions"
        assert transcriber.model_name == "whisper-large-v3"

    def test_apitranscriber_init_strips_trailing_slash(self, mock_pyqt_signal):
        from src.core.api_transcriber import APITranscriber

        transcriber = APITranscriber("http://localhost:8080/", "whisper-large-v3")
        assert transcriber.base_url == "http://localhost:8080"
        assert transcriber.api_endpoint == "http://localhost:8080/v1/audio/transcriptions"

    def test_apitranscriber_set_audio(self, mock_pyqt_signal):
        from src.core.api_transcriber import APITranscriber

        transcriber = APITranscriber("http://localhost:8080", "whisper-large-v3")
        transcriber.set_audio(b"test audio data")
        assert transcriber.audio_data == b"test audio data"

    def test_apitranscriber_run_no_audio_emits_error(self, mock_pyqt_signal, mock_requests, app):
        from src.core.api_transcriber import APITranscriber

        transcriber = APITranscriber("http://localhost:8080", "whisper-large-v3")
        errors = []
        transcriber.error.connect(errors.append)
        transcriber.run()

        assert len(errors) == 1
        assert "No audio" in errors[0]

    def test_apitranscriber_run_success_emits_finished(self, mock_pyqt_signal, mock_requests, app):
        from src.core.api_transcriber import APITranscriber

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "transcribed text"}
        mock_requests.post.return_value = mock_response

        transcriber = APITranscriber("http://localhost:8080", "whisper-large-v3")
        transcriber.set_audio(b"audio data")
        results = []
        transcriber.finished.connect(results.append)
        transcriber.run()

        assert len(results) == 1
        assert results[0] == "transcribed text"

    def test_apitranscriber_run_401_emits_error(self, mock_pyqt_signal, mock_requests, app):
        from src.core.api_transcriber import APITranscriber

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_requests.post.return_value = mock_response

        transcriber = APITranscriber("http://localhost:8080", "whisper-large-v3")
        transcriber.set_audio(b"audio data")
        errors = []
        transcriber.error.connect(errors.append)
        transcriber.run()

        assert len(errors) == 1
        assert "401" in errors[0]

    def test_apitranscriber_run_429_emits_error(self, mock_pyqt_signal, mock_requests, app):
        from src.core.api_transcriber import APITranscriber

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"
        mock_requests.post.return_value = mock_response

        transcriber = APITranscriber("http://localhost:8080", "whisper-large-v3")
        transcriber.set_audio(b"audio data")
        errors = []
        transcriber.error.connect(errors.append)
        transcriber.run()

        assert len(errors) == 1
        assert "429" in errors[0]

    def test_apitranscriber_run_strips_whitespace(self, mock_pyqt_signal, mock_requests, app):
        from src.core.api_transcriber import APITranscriber

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "  hello world  "}
        mock_requests.post.return_value = mock_response

        transcriber = APITranscriber("http://localhost:8080", "whisper-large-v3")
        transcriber.set_audio(b"audio data")
        results = []
        transcriber.finished.connect(results.append)
        transcriber.run()

        assert results[0] == "hello world"

    def test_apitranscriber_run_sets_last_result(self, mock_pyqt_signal, mock_requests, app):
        from src.core.api_transcriber import APITranscriber

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "last result text"}
        mock_requests.post.return_value = mock_response

        transcriber = APITranscriber("http://localhost:8080", "whisper-large-v3")
        transcriber.set_audio(b"audio data")
        transcriber.run()

        assert transcriber.last_result == "last result text"

    def test_apitranscriber_run_requests_exception(self, mock_pyqt_signal, mock_requests, app):
        import requests as req

        from src.core.api_transcriber import APITranscriber

        mock_requests.post.side_effect = req.exceptions.Timeout("read timed out")

        transcriber = APITranscriber("http://localhost:8080", "whisper-large-v3")
        transcriber.set_audio(b"audio data")
        errors = []
        transcriber.error.connect(errors.append)
        transcriber.run()

        assert len(errors) == 1
        assert "Connection" in errors[0]

    def test_apitranscriber_run_generic_exception(self, mock_pyqt_signal, mock_requests, app):
        from src.core.api_transcriber import APITranscriber

        mock_requests.post.side_effect = ValueError("bad response")

        transcriber = APITranscriber("http://localhost:8080", "whisper-large-v3")
        transcriber.set_audio(b"audio data")
        errors = []
        transcriber.error.connect(errors.append)
        transcriber.run()

        assert len(errors) == 1
        assert "Unexpected" in errors[0]

    def test_transcribe_generic_exception(self, mock_requests, app):

        from src.core.api_transcriber import transcribe

        mock_requests.post.side_effect = ValueError("internal error")

        errors = []
        result = transcribe(
            api_endpoint="http://localhost:8080/v1/audio/transcriptions",
            model_name="whisper-large-v3",
            audio_data=b"fake wav",
            error_cb=errors.append,
        )

        assert result is None
        assert len(errors) == 1
        assert "Unexpected" in errors[0]
