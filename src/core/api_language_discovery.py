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
