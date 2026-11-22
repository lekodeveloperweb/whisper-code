from unittest.mock import MagicMock, patch

import pytest
import requests

from src.core.api_language_discovery import (
    LanguageDiscoveryError,
    fetch_model_languages,
)

MODEL_ID = "Systran/faster-whisper-small"
EXPECTED_TIMEOUT_SECONDS = 10


def model_response(records):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"data": records}
    return response


def test_filters_exact_asr_model_and_app_languages():
    records = [
        {"id": MODEL_ID, "task": "automatic-speech-recognition", "language": ["en", "pt", "es"]},
        {"id": "other/asr", "task": "automatic-speech-recognition", "language": ["pt"]},
        {"id": "kokoro/tts", "task": "text-to-speech", "language": ["en", "pt"]},
    ]
    with patch(
        "src.core.api_language_discovery.requests.get", return_value=model_response(records)
    ):
        assert fetch_model_languages("http://stt", MODEL_ID, None) == ["en", "pt"]


def test_accepts_exact_model_languages_when_speaches_omits_task_metadata():
    records = [{"id": MODEL_ID, "language": ["en", "pt"]}]
    with patch(
        "src.core.api_language_discovery.requests.get", return_value=model_response(records)
    ):
        assert fetch_model_languages("http://stt", MODEL_ID, None) == ["en", "pt"]


def test_request_uses_models_path_bearer_and_empty_headers():
    records = [{"id": MODEL_ID, "task": "automatic-speech-recognition", "language": ["en", "pt"]}]
    request = model_response(records)
    with patch("src.core.api_language_discovery.requests.get", return_value=request) as get:
        fetch_model_languages("http://stt/", MODEL_ID, "k1")
        assert get.call_args.args == ("http://stt/v1/models",)
        assert get.call_args.kwargs["headers"] == {"Authorization": "Bearer k1"}
        assert get.call_args.kwargs["timeout"] == EXPECTED_TIMEOUT_SECONDS
        assert get.call_count == 1
        fetch_model_languages("http://stt", MODEL_ID, None)
    assert get.call_args.kwargs["headers"] == {}


@pytest.mark.parametrize(
    "records",
    [
        [],
        [{"id": MODEL_ID, "task": "text-to-speech", "language": ["en", "pt"]}],
        [{"id": MODEL_ID, "task": "automatic-speech-recognition"}],
        [{"id": MODEL_ID, "task": "automatic-speech-recognition", "language": "en"}],
    ],
)
def test_missing_model_or_invalid_language_metadata_raises(records):
    with (
        patch("src.core.api_language_discovery.requests.get", return_value=model_response(records)),
        pytest.raises(LanguageDiscoveryError),
    ):
        fetch_model_languages("http://stt", MODEL_ID, None)


@pytest.mark.parametrize("failure", ["http", "json", "timeout"])
def test_transport_failures_raise_language_error(failure):
    request = MagicMock()
    request.raise_for_status.return_value = None
    if failure == "http":
        request.raise_for_status.side_effect = requests.HTTPError("401")
    elif failure == "json":
        request.json.side_effect = ValueError("invalid JSON")
    get_patch = patch("src.core.api_language_discovery.requests.get", return_value=request)
    if failure == "timeout":
        get_patch = patch(
            "src.core.api_language_discovery.requests.get",
            side_effect=requests.Timeout("timed out"),
        )
    with get_patch as get, pytest.raises(LanguageDiscoveryError):
        fetch_model_languages("http://stt", MODEL_ID, None)
    assert get.call_args.kwargs["timeout"] == EXPECTED_TIMEOUT_SECONDS
