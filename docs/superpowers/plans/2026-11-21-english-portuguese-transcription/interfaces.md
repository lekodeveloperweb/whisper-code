# Shared Implementation Interfaces

This file is the single source for new shared definitions. Task files reference these definitions; they do not duplicate their implementation. Existing `ConfigManager`, `SettingsDialog`, `APITranscriber`, `WhisperCodeApp`, and `GrammarChecker` bodies are changed with targeted edits that preserve unrelated existing behavior.

## `src/utils/config_manager.py` — canonical application constants

Add these definitions once near the module's other configuration constants, then reference them from defaults, `ENV_MAP`, discovery, transcription, and grammar refinement as indicated by each task.

```python
APP_LANGUAGE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("en", "English"),
    ("pt", "Portuguese"),
)
DEFAULT_TRANSCRIPTION_LANGUAGE = "en"
LANGUAGE_CONFIG_KEY = "transcription_language"
LANGUAGE_ENV_VAR = "WHISPER_TRANSCRIPTION_LANGUAGE"
MULTILINGUAL_STT_MODEL_ID = "Systran/faster-whisper-small"
```

In `DEFAULT_CONFIG`, use these existing names as values:

```python
DEFAULT_CONFIG.update(
    {
        "model_name": MULTILINGUAL_STT_MODEL_ID,
        LANGUAGE_CONFIG_KEY: DEFAULT_TRANSCRIPTION_LANGUAGE,
    }
)
```

In `ENV_MAP`, add:

```python
ENV_MAP.update({LANGUAGE_CONFIG_KEY: (LANGUAGE_ENV_VAR, str)})
```

Preserve the current merge precedence and retain any `model_name` explicitly present in `settings.json`.

## `src/core/api_language_discovery.py` — discovery implementation

Create this module with the following complete implementation. `auth_headers` is the existing utility at `src/utils/auth_headers.py`.

```python
from __future__ import annotations

from typing import TypedDict

import requests

from src.utils.auth_headers import auth_headers
from src.utils.config_manager import APP_LANGUAGE_OPTIONS

SPEACHES_MODELS_PATH = "/v1/models"
SPEACHES_ASR_TASK = "automatic-speech-recognition"
LANGUAGE_DISCOVERY_TIMEOUT_SECONDS = 10


class SpeachesModelRecord(TypedDict, total=False):
    id: str
    task: str
    language: list[str]


class SpeachesModelsResponse(TypedDict):
    data: list[SpeachesModelRecord]


class LanguageDiscoveryError(Exception):
    """The configured model's advertised language capabilities are unavailable."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


def fetch_model_languages(
    stt_api_url: str,
    model_id: str,
    api_key: str | None,
) -> list[str]:
    """Return this configured ASR model's supported app language codes.

    Codes are returned in APP_LANGUAGE_OPTIONS order. Network, HTTP, JSON,
    response-shape, model-match, explicit non-ASR task, or language-metadata
    failures are reported as LanguageDiscoveryError. Speaches versions that
    omit task metadata are supported when the exact model advertises a valid
    language list. No app-language overlap returns an empty list.
    """
    url = f"{stt_api_url.rstrip('/')}{SPEACHES_MODELS_PATH}"
    try:
        response = requests.get(
            url,
            headers=auth_headers(api_key),
            timeout=LANGUAGE_DISCOVERY_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload: object = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise LanguageDiscoveryError("Unable to read model language capabilities") from exc

    if not isinstance(payload, dict):
        raise LanguageDiscoveryError("Invalid model-list response")
    records = payload.get("data")
    if not isinstance(records, list):
        raise LanguageDiscoveryError("Invalid model-list response")

    model_record: dict[str, object] | None = None
    for record in records:
        if isinstance(record, dict) and record.get("id") == model_id:
            model_record = record
            break
    if model_record is None:
        raise LanguageDiscoveryError("Configured model was not found")
    task = model_record.get("task")
    if task is not None and task != SPEACHES_ASR_TASK:
        raise LanguageDiscoveryError("Configured model is not an ASR model")

    raw_languages = model_record.get("language")
    if not isinstance(raw_languages, list) or not all(
        isinstance(code, str) for code in raw_languages
    ):
        raise LanguageDiscoveryError("Configured model has no valid language metadata")

    advertised = set(raw_languages)
    return [code for code, _label in APP_LANGUAGE_OPTIONS if code in advertised]
```

## `src/gui/settings_dialog.py` — asynchronous worker

Add this worker class to the settings module. The dialog connects `languages_ready` and `failed` to its UI-state handlers, keeps a reference to the worker until it finishes, and starts it on initial dialog load and when Refresh/Retry is activated.

```python
from PySide6.QtCore import QThread
from PySide6.QtCore import Signal

from src.core.api_language_discovery import (
    LanguageDiscoveryError,
    fetch_model_languages,
)


class _LanguageDiscoveryWorker(QThread):
    languages_ready = Signal(list)
    failed = Signal(str)

    def __init__(
        self,
        stt_api_url: str,
        model_id: str,
        api_key: str | None,
    ) -> None:
        super().__init__()
        self._stt_api_url = stt_api_url
        self._model_id = model_id
        self._api_key = api_key

    def run(self) -> None:
        try:
            languages = fetch_model_languages(
                self._stt_api_url,
                self._model_id,
                self._api_key,
            )
        except LanguageDiscoveryError as exc:
            self.failed.emit(str(exc))
            return
        self.languages_ready.emit(languages)
```

The visible error handler must use only the sanitized error message from `LanguageDiscoveryError`; it must not interpolate the API key or raw response body.

## `src/core/api_transcriber.py` — multipart helper

Add the constant and helper below. `APITranscriber` stores the selected code, and the existing module-level `transcribe` call builds its form data with this helper so the field name is defined once.

```python
LANGUAGE_REQUEST_FIELD = "language"


def transcription_form_data(model_name: str, language: str) -> dict[str, str]:
    """Return the multipart scalar fields sent to the STT endpoint."""
    return {
        "model": model_name,
        LANGUAGE_REQUEST_FIELD: language,
    }
```

Call-site contract:

- Add `language: str = DEFAULT_TRANSCRIPTION_LANGUAGE` to `APITranscriber` construction and store it as `self.language`.
- Add `language: str = DEFAULT_TRANSCRIPTION_LANGUAGE` to the existing module-level `transcribe` function without breaking existing callers.
- Pass `transcription_form_data(model_name, language)` as the existing POST `data` argument.
- `APITranscriber.run()` passes `self.language` to the module-level function.
- `WhisperCodeApp._make_transcriber()` passes `ConfigManager.get(LANGUAGE_CONFIG_KEY)` with the default applied; `_apply_settings()` updates `self.transcriber.language` from the reloaded config.

## `src/core/grammar_checker.py` — same-language instruction

Add the prompt constant once and include it in the existing system prompt string. Keep the user message content as the original transcript string.

```python
GRAMMAR_LANGUAGE_PRESERVATION_INSTRUCTION = "Preserve the input language. Do not translate."
```

## K3 and response-schema invariants

`SPEACHES_MODELS_RESPONSE_SHAPE = {"data": [{"id": str, "task"?: str, "language": list[str]}]}` is the wire contract implemented by `SpeachesModelsResponse` and `SpeachesModelRecord` above; `task` may be omitted by Speaches 0.7.0, but when present must identify ASR; it is not a second runtime setting.

The deployment values consumed by Task 5 are:

```python
SPEACHES_IMAGE_VERSION = "0.7.0"
K3_DEFAULT_LANGUAGE = "en"
K3_INFERENCE_DEVICE = "cpu"
K3_COMPUTE_TYPE = "int8"
K3_CPU_THREADS = 8
K3_MEMORY_LIMIT_GIB = 4
```
