# Task 4

Send the selected language through transcription and preserve it in refinement

**Files:**

- Modify: `src/core/api_transcriber.py`
- Modify: `src/whisper_code/cli.py`
- Modify: `src/core/grammar_checker.py`
- Modify/Test: `tests/test_api_transcriber.py`
- Modify/Test: `tests/test_cli.py`
- Modify/Test: `tests/test_grammar_checker.py`

**Interfaces:**

- Consumes: config constants from Task 1; `LANGUAGE_REQUEST_FIELD`, `transcription_form_data`, and `GRAMMAR_LANGUAGE_PRESERVATION_INSTRUCTION` from `../interfaces.md`; Settings persistence from Tasks 2-3.
- Produces: transcriber language property, explicit multipart language field, app startup/hot-reload wiring, same-language grammar prompt.

**Task-boundary preconditions for RED:** Tasks 1-3 are complete; Settings can save a valid language code; the transcriber currently posts only its model/audio fields; grammar refinement has no language-preservation instruction.

**Required test-harness setup:** Reuse the existing request mocks and Qt/app fixtures in the named tests. Mock transcription/chat HTTP responses; make no real API calls.

- [x] Step 1: Write the failing tests

Add to `tests/test_api_transcriber.py`:

```python
from unittest.mock import MagicMock, patch

from src.core.api_transcriber import APITranscriber, transcribe

MODEL_ID = "Systran/faster-whisper-small"


def successful_transcription_response():
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"text": "Olá, mundo."}
    return response


def test_module_transcribe_posts_explicit_language():
    with patch(
        "src.core.api_transcriber.requests.post", return_value=successful_transcription_response()
    ) as post:
        transcribe("http://stt", MODEL_ID, b"wav-bytes", language="pt")
    assert post.call_args.kwargs["data"] == {"model": MODEL_ID, "language": "pt"}


def test_api_transcriber_run_posts_its_language():
    transcriber = APITranscriber("http://stt", MODEL_ID, language="pt")
    transcriber.audio_data = b"wav-bytes"
    with patch(
        "src.core.api_transcriber.requests.post", return_value=successful_transcription_response()
    ) as post:
        transcriber.run()
    assert post.call_args.kwargs["data"] == {"model": MODEL_ID, "language": "pt"}


def test_language_defaults_to_english_for_class_and_function():
    transcriber = APITranscriber("http://stt", MODEL_ID)
    assert transcriber.language == "en"
    with patch(
        "src.core.api_transcriber.requests.post", return_value=successful_transcription_response()
    ) as post:
        transcribe("http://stt", MODEL_ID, b"wav-bytes")
    assert post.call_args.kwargs["data"] == {"model": MODEL_ID, "language": "en"}
```

Add to `tests/test_grammar_checker.py`:

```python
def test_portuguese_refinement_prompt_preserves_language(mock_requests, app):
    from src.core.grammar_checker import check_grammar

    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"choices": [{"message": {"content": "Olá, mundo."}}]}
    mock_requests.post.return_value = response
    check_grammar(
        "http://llm/v1/chat/completions",
        "grammar-model",
        "Olá, mundo.",
    )
    payload = mock_requests.post.call_args.kwargs["json"]
    assert "Preserve the input language. Do not translate." in payload["messages"][0]["content"]
    assert payload["messages"][1]["content"] == "Olá, mundo."
```

Add `test_transcription_language_initializes_and_hot_reloads` beside the existing CLI transcriber/hot-reload tests: apply the same fixture setup, initialize config with `model_name="Systran/faster-whisper-small"` and `transcription_language="pt"`, assert the new transcriber has that exact model ID and `language == "pt"`, change config to `en`, call `_apply_settings()`, and assert the existing transcriber retains the same model ID and now has `language == "en"`. Add `test_settings_acceptance_persists_selected_language_to_file` using the current app settings-saved signal and a temporary ConfigManager home: select `pt`, accept Settings, reload ConfigManager, and assert its `transcription_language` is `pt`.

Add `test_portuguese_transcript_is_injected_without_translation` to `tests/test_cli.py` beside the existing transcription-success tests, reusing its app/injector fixtures: call the transcription-success handler with `"Olá, mundo."` while `use_grammar_check` is false; assert the injector receives exactly that string and the mocked chat endpoint is not called.

- [x] Step 2: RED GATE

Run: `uv run pytest tests/test_api_transcriber.py tests/test_cli.py tests/test_grammar_checker.py tests/test_integration.py -q`

Expected RED: the API request assertion names the missing `language` field or class property, the persisted-settings test names the missing `transcription_language` value, or the grammar assertion names the missing preservation instruction. Paste the actual output.

- [x] Step 3: Implement

Use `transcription_form_data()` from `../interfaces.md`. Add the language constructor/function defaults and pass the class property through `APITranscriber.run()`. Wire `WhisperCodeApp._make_transcriber()` and `_apply_settings()` to the configured code without changing URL/key/model behavior. Append the grammar preservation constant to the existing system prompt; do not change the user message shape or add a translation request.

- [x] Step 4: GREEN

Run: `uv run pytest tests/test_api_transcriber.py tests/test_cli.py tests/test_grammar_checker.py tests/test_integration.py -q`

Expected output: all named tests pass. They catch dropped/incorrect language form data, missing hot reload, grammar prompts that allow translation, or a Portuguese transcript changed before injection when grammar checking is disabled.

- [x] Step 5: Record completion evidence

Record the exact command and actual output. Do not commit.
