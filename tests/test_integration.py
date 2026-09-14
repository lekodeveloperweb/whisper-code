"""Integration tests for the full dictation flow.

Tests the end-to-end pipeline:
  AudioRecorder (mocked PyAudio)
    → APITranscriber (mocked requests)
    → TextInjector (mocked pyperclip)

Uses the callback-based `transcribe()` function from api_transcriber.py
so we don't need a running Qt event loop.
"""

from unittest.mock import MagicMock, patch

import pytest

HIGH_CONFIDENCE = 0.95


@pytest.fixture
def mock_pyaudio():
    """Mock PyAudio so AudioRecorder works without a real mic."""
    with patch("pyaudio.PyAudio") as mock:
        mock_instance = MagicMock()
        mock_instance.get_sample_size.return_value = 2
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_requests():
    """Mock the requests module for API calls."""
    with patch("src.core.api_transcriber.requests") as mock:
        yield mock


@pytest.fixture
def mock_pyperclip():
    """Mock pyperclip for text injection tests."""
    with patch("src.utils.text_injector.pyperclip") as mock:
        mock.paste.return_value = ""  # empty paste so restore doesn't overwrite
        yield mock


def test_full_dictation_flow(mock_pyaudio, mock_requests, mock_pyperclip):
    """Record audio → transcribe via mock API → inject text.

    This tests the core integration path:
    AudioRecorder (mocked) → transcribe() (mocked requests) → pyperclip (mocked)
    """
    from src.core.api_transcriber import transcribe
    from src.core.audio_recorder import AudioRecorder

    # --- Step 1: Capture audio (mocked) ---
    stream = MagicMock()
    stream.read.return_value = b"\x00\x7f" * 1024  # 1024 samples × 2 bytes, loud audio
    mock_pyaudio.open.return_value = stream

    recorder = AudioRecorder(sample_rate=16000)
    recorder.start_recording()

    import time

    time.sleep(0.05)  # let background thread collect frames

    audio_data = recorder.stop_recording()
    assert audio_data, "Recorder should return WAV bytes"
    assert len(audio_data) > 0

    # --- Step 2: Transcribe via mock API ---
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "hello world"}
    mock_requests.post.return_value = mock_response

    results = []
    result = transcribe(
        api_endpoint="http://localhost:8080/v1/audio/transcriptions",
        model_name="whisper-large-v3",
        audio_data=audio_data,
        finished_cb=results.append,
    )

    assert result == "hello world"
    assert len(results) == 1
    assert results[0] == "hello world"
    mock_requests.post.assert_called_once()

    # --- Step 3: Inject text (mocked clipboard) ---
    from src.utils.text_injector import TextInjector

    with (
        patch("src.utils.text_injector.check_accessibility_permission", return_value=True),
        patch("src.utils.text_injector.Controller") as mock_ctrl,
    ):
        keyboard = MagicMock()
        mock_ctrl.return_value = keyboard
        keyboard.pressed.return_value.__enter__ = MagicMock()
        keyboard.pressed.return_value.__exit__ = MagicMock()

        injector = TextInjector()
        injector.inject_text("hello world")

    mock_pyperclip.copy.assert_any_call("hello world")


def test_empty_audio_emits_error(mock_pyaudio, mock_requests):
    """Empty audio data should trigger error callback."""
    from src.core.api_transcriber import transcribe

    errors = []
    result = transcribe(
        api_endpoint="http://localhost:8080/v1/audio/transcriptions",
        model_name="whisper-large-v3",
        audio_data=None,
        error_cb=errors.append,
    )

    assert result is None
    assert len(errors) == 1
    assert "No audio" in errors[0]


def test_api_error_propagates_to_callback(mock_pyaudio, mock_requests):
    """API 500 error should emit error callback."""
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

    assert result is None
    assert len(errors) == 1
    assert "500" in errors[0]


def test_connection_error_propagates(mock_pyaudio):
    """Connection refused should emit error callback."""
    import requests as req

    from src.core.api_transcriber import transcribe

    with patch("src.core.api_transcriber.requests") as mock_requests:
        mock_requests.post.side_effect = req.exceptions.ConnectionError("refused")

        errors = []
        result = transcribe(
            api_endpoint="http://localhost:9999/v1/audio/transcriptions",
            model_name="whisper-large-v3",
            audio_data=b"fake wav",
            error_cb=errors.append,
        )

        assert result is None
        assert len(errors) == 1
        assert "Connection" in errors[0]


def test_confidence_score_propagates(mock_pyaudio, mock_requests):
    """Confidence from API should reach callback."""
    from src.core.api_transcriber import transcribe

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "hello", "confidence": 0.95}
    mock_requests.post.return_value = mock_response

    confidences = []
    result = transcribe(
        api_endpoint="http://localhost:8080/v1/audio/transcriptions",
        model_name="whisper-large-v3",
        audio_data=b"fake wav",
        confidence_cb=confidences.append,
    )

    assert result == "hello"
    assert len(confidences) == 1
    assert confidences[0] == HIGH_CONFIDENCE


def test_text_injection_uses_pyperclip(mock_pyperclip):
    """TextInjector should copy text to clipboard."""
    from src.utils.text_injector import TextInjector

    with (
        patch("src.utils.text_injector.check_accessibility_permission", return_value=True),
        patch("src.utils.text_injector.Controller") as mock_ctrl,
    ):
        keyboard = MagicMock()
        mock_ctrl.return_value = keyboard
        keyboard.pressed.return_value.__enter__ = MagicMock()
        keyboard.pressed.return_value.__exit__ = MagicMock()

        injector = TextInjector()
        injector.inject_text("test text")

    mock_pyperclip.copy.assert_any_call("test text")
