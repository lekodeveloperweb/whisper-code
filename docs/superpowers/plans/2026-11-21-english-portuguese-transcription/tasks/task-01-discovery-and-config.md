# Task 1

Implement configured-model language discovery and configuration defaults

**Files:** Create `src/core/api_language_discovery.py` and `tests/test_api_language_discovery.py`; modify `src/utils/config_manager.py` and `tests/test_config.py`.

**Interfaces:** Consume existing `src.utils.auth_headers.auth_headers` and the constants/`fetch_model_languages` implementation from `../interfaces.md`. Produce `APP_LANGUAGE_OPTIONS`, `DEFAULT_TRANSCRIPTION_LANGUAGE`, `LANGUAGE_CONFIG_KEY`, `LANGUAGE_ENV_VAR`, `MULTILINGUAL_STT_MODEL_ID`, `SPEACHES_MODELS_PATH`, `SPEACHES_MODELS_RESPONSE_SHAPE`, `SPEACHES_ASR_TASK`, `LANGUAGE_DISCOVERY_TIMEOUT_SECONDS`, `SpeachesModelRecord`, `SpeachesModelsResponse`, `LanguageDiscoveryError`, and `fetch_model_languages`.

**Task-boundary preconditions for RED:** `auth_headers` exists; `api_language_discovery.py` does not; `ConfigManager` has no transcription-language key and defaults `model_name` to the pre-feature value.

**Required test-harness setup:** Mock `src.core.api_language_discovery.requests.get`. For config tests, set `HOME` to `tmp_path`, remove relevant `WHISPER_*` environment variables, and use the existing `~/.config/whisper-code/settings.json` path.

- [x] Step 1: Write the failing tests

Add to `tests/test_api_language_discovery.py`:

```python
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
```

Add to `tests/test_config.py` (retain its existing tests and imports):

```python
import json
from src.utils.config_manager import ConfigManager


def isolate_config_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("WHISPER_TRANSCRIPTION_LANGUAGE", raising=False)
    monkeypatch.delenv("WHISPER_MODEL_NAME", raising=False)
    return tmp_path / ".config" / "whisper-code" / "settings.json"


def test_transcription_language_and_model_defaults(monkeypatch, tmp_path):
    isolate_config_home(monkeypatch, tmp_path)
    config = ConfigManager()
    assert config.get("transcription_language") == "en"
    assert config.get("model_name") == "Systran/faster-whisper-small"


def test_language_environment_override_and_saved_model_preservation(monkeypatch, tmp_path):
    settings_path = isolate_config_home(monkeypatch, tmp_path)
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"transcription_language": "en", "model_name": "custom/model"})
    )
    monkeypatch.setenv("WHISPER_TRANSCRIPTION_LANGUAGE", "pt")
    config = ConfigManager()
    assert config.get("transcription_language") == "pt"
    assert config.get("model_name") == "custom/model"
```

- [x] Step 2: RED GATE

Run: `uv run pytest tests/test_api_language_discovery.py tests/test_config.py -q`

Expected RED: the new module import fails with `ModuleNotFoundError` naming `src.core.api_language_discovery`; if the module exists due an earlier task, the language/model-default assertions must fail by name. Paste the actual output.

- [x] Step 3: Implement

Copy the complete discovery constants, error class, and `fetch_model_languages` body from `../interfaces.md`. Add the constants to `config_manager.py`; use the constants in `DEFAULT_CONFIG` and `ENV_MAP`. Preserve explicit saved `model_name` values and current environment precedence.

- [x] Step 4: GREEN

Run: `uv run pytest tests/test_api_language_discovery.py tests/test_config.py -q`

Expected output: all discovery/config tests pass. These tests catch wrong endpoint/auth, explicit task/model mismatch, Speaches responses that omit task metadata, unsupported-code leakage, timeout drift, default drift, and accidental rewriting of a saved model name. The compatibility regression test is `test_accepts_exact_model_languages_when_speaches_omits_task_metadata`.

- [x] Step 5: Record completion evidence

Record the exact command and actual output. Do not commit.
