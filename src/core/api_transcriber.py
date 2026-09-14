from __future__ import annotations

from collections.abc import Callable

import requests
from PySide6.QtCore import QThread
from PySide6.QtCore import Signal as pyqtSignal
from requests.exceptions import RequestException as RequestsException

HTTP_OK = 200

TranscribeFinishedCb = Callable[[str], None]
TranscribeErrorCb = Callable[[str], None]
TranscribeConfidenceCb = Callable[[float], None]


class APITranscriber(QThread):
    """Send audio to an OpenAI-compatible STT API in a background thread.

    POSTs WAV audio to /v1/audio/transcriptions and emits Qt signals
    on completion (success or error). Tracks the last result for
    fallback access from the grammar checker.
    """

    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    confidence_changed = pyqtSignal(float)

    def __init__(self, api_url: str, model_name: str) -> None:
        """Initialize the transcriber with API URL and model name.

        Args:
            api_url: Base URL of the STT API (e.g. http://localhost:8080).
            model_name: Model identifier for transcription.
        """
        super().__init__()
        self.base_url: str = api_url.rstrip("/")
        self.api_endpoint: str = f"{self.base_url}/v1/audio/transcriptions"
        self.model_name: str = model_name
        self.audio_data: bytes | None = None
        self.last_result: str = ""

    def set_audio(self, audio_data: bytes) -> None:
        """Set the WAV audio bytes to transcribe."""
        self.audio_data = audio_data

    def run(self) -> None:
        """Execute the transcription request in a background thread.

        Sends the audio to the API and emits signals on success or
        error. Catches both RequestsException and generic exceptions.
        """
        if not self.audio_data:
            self.error.emit("No audio data provided")
            return

        try:
            files: dict[str, tuple[str, bytes, str]] = {
                "file": ("audio.wav", self.audio_data, "audio/wav")
            }
            payload: dict[str, str] = {"model": self.model_name}

            response = requests.post(self.api_endpoint, files=files, data=payload, timeout=120)

            if response.status_code == HTTP_OK:
                response_json = response.json()
                text: str = response_json.get("text", "").strip()
                self.last_result = text
                confidence: float | None = response_json.get("confidence")
                if confidence is not None:
                    self.confidence_changed.emit(float(confidence))
                self.finished.emit(text)
            else:
                self.error.emit(f"API Error (Status {response.status_code}): {response.text}")

        except RequestsException as e:
            error_msg = f"Connection error: {str(e)}"
            self.error.emit(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.error.emit(error_msg)


def _handle_error(error_cb: TranscribeErrorCb | None, error_msg: str) -> None:
    """Invoke error callback if provided."""
    if error_cb:
        error_cb(error_msg)


def _process_success(
    response: requests.Response,
    finished_cb: TranscribeFinishedCb | None,
    confidence_cb: TranscribeConfidenceCb | None,
) -> str:
    """Process a successful API response and return the transcribed text.

    Args:
        response: The successful HTTP response from the API.
        finished_cb: Callback invoked with the transcribed text.
        confidence_cb: Callback invoked with the confidence score.

    Returns:
        The transcribed text string.
    """
    response_json = response.json()
    text: str = response_json.get("text", "").strip()
    confidence: float | None = response_json.get("confidence")
    if confidence_cb and confidence is not None:
        confidence_cb(float(confidence))
    if finished_cb:
        finished_cb(text)
    return text


def transcribe(
    api_endpoint: str,
    model_name: str,
    audio_data: bytes | None,
    finished_cb: TranscribeFinishedCb | None = None,
    error_cb: TranscribeErrorCb | None = None,
    confidence_cb: TranscribeConfidenceCb | None = None,
) -> str | None:
    """Core transcription logic. Extracted for testability.

    Accepts callback functions instead of Qt signals so it can be
    tested without a running Qt event loop.

    Args:
        api_endpoint: Full endpoint URL for the STT API.
        model_name: Model identifier for transcription.
        audio_data: WAV audio bytes to transcribe.
        finished_cb: Callback invoked with the transcribed text.
        error_cb: Callback invoked on errors.
        confidence_cb: Callback invoked with the confidence score.

    Returns:
        The transcribed text on success, None on failure.
    """
    if not audio_data:
        _handle_error(error_cb, "No audio data provided")
        return None

    try:
        files: dict[str, tuple[str, bytes, str]] = {"file": ("audio.wav", audio_data, "audio/wav")}
        payload: dict[str, str] = {"model": model_name}

        response = requests.post(api_endpoint, files=files, data=payload, timeout=120)

        if response.status_code == HTTP_OK:
            return _process_success(response, finished_cb, confidence_cb)
        if error_cb:
            error_cb(f"API Error (Status {response.status_code}): {response.text}")
        return None

    except RequestsException as e:
        error_msg = f"Connection error: {str(e)}"
        _handle_error(error_cb, error_msg)
        return None
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        _handle_error(error_cb, error_msg)
        return None
