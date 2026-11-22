# English and Portuguese Transcription Design

**Date:** 2026-11-21 **Status:** Draft

## Overview

Whisper-Code will let users manually choose English or Portuguese as the language they are speaking. The selected language is sent to the configured STT model, which returns a transcript in that language; this feature does not translate text or auto-detect the spoken language. The K3 Speaches deployment will use a multilingual Whisper model that advertises both languages.

## Design

### Language capability discovery (`src/core/api_language_discovery.py`, new)

Add:

```python
class LanguageDiscoveryError(Exception):
    """The configured STT model's language capabilities could not be read."""


def fetch_model_languages(
    stt_api_url: str,
    model_id: str,
    api_key: str | None,
) -> list[str]:
    """Return supported app language codes for the exact configured ASR model."""
```

The function sends an authenticated `GET` to `{stt_api_url.rstrip('/')}/v1/models` using the existing `auth_headers` helper and a 10-second timeout. It parses Speaches model-list responses shaped as `{"data": [{"id": str, "task"?: str, "language": [str, ...]}]}`; it matches the exact effective model ID, rejects a supplied task unless it is `automatic-speech-recognition`, and accepts omitted task metadata for compatibility with the deployed Speaches 0.7.0 response. The return value is the intersection of the record's language codes and the ordered app language options `en`, then `pt`.

A request/HTTP/JSON failure, a missing exact model record, an explicitly non-ASR task, or missing/invalid `language` metadata raises `LanguageDiscoveryError`. A valid record whose languages have no intersection with `en`/`pt` returns an empty list. The UI treats both cases as unavailable capabilities, but distinguishes an API error from a valid model that supports neither app language. This is Speaches-specific metadata; other OpenAI-compatible APIs that omit the required exact model or language fields do not get a fabricated language list.

The helper is tested with mocked HTTP responses. It does not download models or query the broader `/v1/registry` catalog; only the configured model already listed by `/v1/models` controls the dropdown.

### Settings and configuration (`src/gui/settings_dialog.py`, `src/utils/config_manager.py`)

Add `transcription_language` to `DEFAULT_CONFIG`, defaulting to `en`, and map it to `WHISPER_TRANSCRIPTION_LANGUAGE` in `ENV_MAP`. Existing environment-over-file-over-default priority is unchanged.

Add a `QComboBox` to the STT Server group with item data codes `en` and `pt` and visible labels English and Portuguese. A `_LanguageDiscoveryWorker` fetches capabilities asynchronously when the dialog opens so network latency does not block the Qt UI. A Refresh/Retry control re-queries using the current STT URL, API key, and effective model fields, allowing a user to change server/model settings and then refresh the choices.

On successful discovery, the combo contains only the intersection returned by `fetch_model_languages`. If the saved code is not supported by the configured model, the combo retains it as an unavailable item and the OK action remains disabled until the user chooses an advertised language. If the model advertises neither English nor Portuguese, Settings explains that the model must be changed and does not accept the dialog.

On a request or metadata error, the combo preserves the saved code and the dialog shows a retryable error. The language control remains unavailable until discovery succeeds; saving unrelated settings remains possible and does not rewrite `transcription_language`. API keys are sent only in the request header and are not shown in status text.

`_apply_config` persists the selected language code. Existing saved `model_name` values remain user-owned and are not automatically rewritten; a saved model ID must match the configured Speaches model for discovery to succeed. New/default configuration uses the same model ID as the K3 deployment.

### Transcription request (`src/core/api_transcriber.py`, `src/whisper_code/cli.py`)

`APITranscriber` stores a `language` value. Add a `language` argument to `APITranscriber` and the module-level `transcribe` function, defaulting to `en` for callers that do not pass a value. The multipart form data contains both the model and `language` fields. `WhisperCodeApp._make_transcriber` initializes the property from `transcription_language`; `_apply_settings` updates it after a settings save, using the same effective model resolution as API capability discovery.

The manual selection is always explicit: both `en` and `pt` are sent in the request. The configured Speaches `DEFAULT_LANGUAGE=en` remains unchanged, and an explicit `pt` request overrides it.

The result continues through the existing transcription/refinement/injection pipeline as a single transcript. No translation endpoint or translation request is added. Because grammar checking is enabled by default, update the system prompt in `src/core/grammar_checker.py` to instruct the editor to preserve the input language and never translate. The prompt remains a string and the user message remains the original transcription string.

### K3 Speaches deployment

Change `K3/speaches/20-config.yaml` in the settings repository from the English-only `Systran/faster-distil-whisper-small.en` model to `Systran/faster-whisper-small`, a multilingual Whisper small model. Keep the current Speaches CPU image version `0.7.0`, `DEFAULT_LANGUAGE=en`, CPU inference, `int8` compute type, eight CPU threads, and 4-GiB memory limit. Change Whisper-Code's default `model_name` to the same model ID so fresh installations request the model whose capabilities the UI checks. Update `K3/speaches/README.md` preload and verification instructions to the new model and verify the authenticated `/v1/models` record advertises both `en` and `pt` after rollout.

Existing `settings.json` model names are not migrated automatically. Documentation will tell existing installations to set Model Name to `Systran/faster-whisper-small` (or another configured model that advertises both `en` and `pt`) when using this K3 deployment. The K3 rollout must pass readiness and model-capability checks within the existing resource limits before the deployment change is considered complete.

### Documentation (non-behavioral, no AC)

Update `docs/configuration.md`, `docs/UI-WIREFRAMES.md`, `docs/PRD.md`, `AGENTS.md`, and `CLAUDE.md` with the setting, environment variable, language choices, model requirement, existing-model-ID migration note, and same-language/no-translation behavior.

### Tests

Add `tests/test_api_language_discovery.py`; extend `tests/test_config.py`, `tests/test_settings_dialog.py`, `tests/test_api_transcriber.py`, `tests/test_cli.py`, and `tests/test_grammar_checker.py`. Extend `tests/test_integration.py` for the same-language transcript path with grammar checking disabled.

## Constants

- `APP_LANGUAGE_OPTIONS = (("en", "English"), ("pt", "Portuguese"))  # exposes only the two requested input languages, exercised by AC-1, AC-2, AC-4, and AC-5`
- `DEFAULT_TRANSCRIPTION_LANGUAGE = "en"  # matches the current Speaches default, exercised by AC-15, AC-22, and AC-25`
- `LANGUAGE_CONFIG_KEY = "transcription_language"  # persisted setting name, exercised by AC-15, AC-16, and AC-19`
- `LANGUAGE_ENV_VAR = "WHISPER_TRANSCRIPTION_LANGUAGE"  # environment override name, exercised by AC-16`
- `SPEACHES_MODELS_PATH = "/v1/models"  # installed-model capability source, exercised by AC-1, AC-7 through AC-14, and AC-26 through AC-28`
- `SPEACHES_MODELS_RESPONSE_SHAPE = {"data": [{"id": str, "task"?: str, "language": list[str]}]}  # task is optional in Speaches 0.7.0; explicit non-ASR task is rejected`
- `SPEACHES_ASR_TASK = "automatic-speech-recognition"  # excludes non-ASR model records, exercised by AC-1 and AC-6`
- `LANGUAGE_REQUEST_FIELD = "language"  # multipart field sent to STT, exercised by AC-21 and AC-22`
- `LANGUAGE_DISCOVERY_TIMEOUT_SECONDS = 10  # bounds a settings capability request, exercised by AC-9`
- `MULTILINGUAL_STT_MODEL_ID = "Systran/faster-whisper-small"  # shared app/K3 model ID, exercised by AC-17, AC-18, AC-20, AC-21, and AC-25`
- `SPEACHES_IMAGE_VERSION = "0.7.0"  # retains the currently deployed API version, exercised by AC-25`
- `K3_DEFAULT_LANGUAGE = "en"  # preserves server default while requests send explicit language, exercised by AC-21, AC-22, and AC-25`
- `K3_INFERENCE_DEVICE = "cpu"  # retains CPU inference, exercised by AC-25`
- `K3_COMPUTE_TYPE = "int8"  # retains CPU quantization, exercised by AC-25`
- `K3_CPU_THREADS = 8  # retains current CPU thread setting, exercised by AC-25`
- `K3_MEMORY_LIMIT_GIB = 4  # retains current pod memory ceiling, exercised by AC-25`
- `GRAMMAR_LANGUAGE_PRESERVATION_INSTRUCTION = "Preserve the input language. Do not translate."  # keeps grammar refinement same-language, exercised by AC-23`

## Acceptance Criteria

1. `GET /v1/models` returns three records: `{"id":"Systran/faster-whisper-small","task":"automatic-speech-recognition","language":["en","pt","es"]}`, `{"id":"other/asr","task":"automatic-speech-recognition","language":["pt"]}`, and `{"id":"kokoro/tts","task":"text-to-speech","language":["en","pt"]}` ⇒ `fetch_model_languages` returns exactly `["en", "pt"]` for `Systran/faster-whisper-small`.
2. The configured ASR model advertises languages `["en", "pt", "es"]` ⇒ the Settings combo contains exactly two choices with item data `en`, `pt` and labels English, Portuguese; it contains no Spanish or Auto-detect choice.
3. The configured model advertises languages `["en", "pt"]` and the saved language is `pt` ⇒ the combo's current item data is `pt`.
4. The configured ASR model advertises only `["en"]` and the saved language is `pt` ⇒ the dialog marks Portuguese unavailable and keeps OK disabled until English is selected.
5. The configured ASR model advertises only `["es"]` and the saved language is `en` ⇒ Settings reports that the model supports neither app language and keeps OK disabled.
6. The exact configured model ID is returned with task `text-to-speech` and languages `["en", "pt"]`, and the saved language is `pt` ⇒ `fetch_model_languages` raises `LanguageDiscoveryError`, Settings preserves `pt`, shows a retryable capability error, and permits saving an unrelated changed preference.
7. `GET /v1/models` returns the configured model record without a `language` field and the saved language is `pt` ⇒ the dialog preserves `pt`, disables the language control, shows the retryable capability error, and permits saving an unrelated changed preference.
8. `GET /v1/models` returns a valid response with no exact configured-model record and the saved language is `pt` ⇒ the dialog preserves `pt`, shows the model-unavailable retry state, and permits saving an unrelated changed preference.
9. A mocked `/v1/models` request raises `requests.Timeout` ⇒ the GET call uses timeout `10`, the dialog preserves the saved language, shows Retry, and permits saving an unrelated changed preference.
10. `GET /v1/models` returns HTTP 401 and the saved language is `pt` ⇒ `fetch_model_languages` raises `LanguageDiscoveryError`, the dialog preserves `pt`, shows Retry, and permits saving an unrelated changed preference.
11. `GET /v1/models` returns HTTP 200 with invalid JSON and the saved language is `pt` ⇒ `fetch_model_languages` raises `LanguageDiscoveryError`, the dialog preserves `pt`, shows Retry, and permits saving an unrelated changed preference.
12. `GET /v1/models` returns the exact configured model with `language="en"` instead of a language-code list and the saved language is `pt` ⇒ `fetch_model_languages` raises `LanguageDiscoveryError`, the dialog preserves `pt`, and permits saving an unrelated changed preference.
13. `fetch_model_languages("http://stt/", "Systran/faster-whisper-small", "k1")` ⇒ the only GET URL is `http://stt/v1/models`, no `/v1/registry` request is sent, and the header is `{"Authorization": "Bearer k1"}`.
14. `fetch_model_languages("http://stt", "Systran/faster-whisper-small", None)` ⇒ the request headers are `{}`.
15. A fresh config with no `transcription_language` value ⇒ `ConfigManager.get("transcription_language") == "en"`.
16. A `settings.json` value `transcription_language="en"` with `WHISPER_TRANSCRIPTION_LANGUAGE="pt"` ⇒ the effective config value is `pt`.
17. A fresh config with no `model_name` in `settings.json` ⇒ `ConfigManager.get("model_name") == "Systran/faster-whisper-small"`.
18. A `settings.json` value `model_name="custom/model"` ⇒ the loaded config retains `custom/model` without migration.
19. A successful dialog with the user selecting `pt` and accepting ⇒ `settings.json` contains `"transcription_language": "pt"`.
20. `WhisperCodeApp` starts with `model_name="Systran/faster-whisper-small"` and `transcription_language="pt"`, then reloads config with `transcription_language="en"` ⇒ the transcriber uses the same effective model ID as discovery, has language `pt` at startup, and has language `en` after `_apply_settings`.
21. `APITranscriber` is constructed with model `Systran/faster-whisper-small` and language `pt`, then runs with audio bytes ⇒ `requests.post` receives multipart form data containing `language="pt"` and model `Systran/faster-whisper-small`.
22. `APITranscriber` is constructed without a language argument ⇒ its language is `en`; calling the core `transcribe` function with audio bytes and no language argument ⇒ `requests.post` receives multipart form data containing `language="en"`.
23. `check_grammar` receives Portuguese text `"Olá, mundo."` ⇒ the system prompt contains `"Preserve the input language. Do not translate."` and the user message content remains `"Olá, mundo."`.
24. A Portuguese transcription response `{"text":"Olá, mundo."}` with grammar checking disabled ⇒ the injector receives exactly `"Olá, mundo."` and no translation request is made.
25. K3 is configured with the currently pinned Speaches 0.7.0 CPU image, model ID `Systran/faster-whisper-small`, `DEFAULT_LANGUAGE=en`, CPU inference, `int8`, eight CPU threads, and a 4-GiB memory limit; after rollout the pod is Ready and the authenticated `/v1/models` response for that exact model has language metadata containing both `en` and `pt` (and, if present, task `automatic-speech-recognition`) ⇒ the K3 model-capability acceptance check passes.
26. Settings opens while the mocked `GET /v1/models` response is pending ⇒ the Qt event loop continues processing a UI event and the dialog remains responsive.
27. The user changes STT URL, API key, and effective model ID in Settings, then activates Refresh ⇒ the worker requests `/v1/models` from the edited URL with the edited key and filters the edited model ID.
28. `/v1/models` returns HTTP 401 for a request using API key `secret-test-key` ⇒ the visible error text does not contain `secret-test-key`.
29. The exact configured model advertises `language=["en", "pt"]` but omits `task`, matching Speaches 0.7.0 ⇒ `fetch_model_languages` returns exactly `["en", "pt"]`; a supplied non-ASR task remains rejected.
