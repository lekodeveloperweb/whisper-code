# Task 2: APITranscriber api_key + run() delegation

**Files:**

- Modify: `src/core/api_transcriber.py`
- Test: `tests/test_api_transcriber.py`

**Interfaces:**

- Consumes: `auth_headers` from task 1 (`src.utils.auth_headers`)
- Produces: `APITranscriber(api_url, model_name, api_key=None)` with
  `self.api_key: str | None`; `transcribe(..., api_key=None)` — consumed by
  task 5 (cli wiring).

- [ ] Step 1: Write the failing tests

APPEND these three tests to `tests/test_api_transcriber.py` (the file
already imports `MagicMock`, `patch`, `pytest`, `QApplication`, and defines
the `mock_requests`, `app`, `mock_pyqt_signal` fixtures):

```python
def test_transcribe_sends_bearer_header(mock_requests, app):
    from src.core.api_transcriber import transcribe

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "hello"}
    mock_requests.post.return_value = mock_response

    transcribe(
        api_endpoint="http://localhost:8080/v1/audio/transcriptions",
        model_name="whisper-large-v3",
        audio_data=b"fake wav",
        api_key="sk-1",
    )

    _, kwargs = mock_requests.post.call_args
    assert kwargs["headers"] == {"Authorization": "Bearer sk-1"}


def test_transcribe_no_key_sends_empty_headers(mock_requests, app):
    from src.core.api_transcriber import transcribe

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "hello"}
    mock_requests.post.return_value = mock_response

    transcribe(
        api_endpoint="http://localhost:8080/v1/audio/transcriptions",
        model_name="whisper-large-v3",
        audio_data=b"fake wav",
        api_key=None,
    )

    _, kwargs = mock_requests.post.call_args
    assert kwargs["headers"] == {}


def test_run_delegates_api_key_to_post(mock_pyqt_signal, mock_requests, app):
    from src.core.api_transcriber import APITranscriber

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "ok"}
    mock_requests.post.return_value = mock_response

    transcriber = APITranscriber("http://localhost:8080", "whisper-large-v3", "k1")
    transcriber.set_audio(b"audio data")
    results = []
    transcriber.finished.connect(results.append)
    transcriber.run()

    assert results == ["ok"]
    assert transcriber.last_result == "ok"
    _, kwargs = mock_requests.post.call_args
    assert kwargs["headers"] == {"Authorization": "Bearer k1"}
```

- [ ] Step 2: RED GATE

Run: `uv run pytest tests/test_api_transcriber.py -v`
Expected output: the three new tests FAIL — the two transcribe tests with
`TypeError: transcribe() got an unexpected keyword argument 'api_key'`,
the run test with `TypeError: __init__() takes 3 positional arguments but 4
were given`. All pre-existing tests still PASS.
PASTE the output.

- [ ] Step 3: Implement

In `src/core/api_transcriber.py`:

1. Add the import `from src.utils.auth_headers import auth_headers`
   (copy from interfaces.md § APITranscriber changes).
2. Replace `__init__` with the block in interfaces.md § Full replacement
   `__init__`.
3. Replace `run` with the block in interfaces.md § Full replacement `run`
   (it now delegates to `transcribe`; the duplicated POST body is gone).
4. Replace the module-level `transcribe` with the block in interfaces.md
   § Full replacement `transcribe`.
   `_handle_error`, `_process_success`, class docstring, and signal
   declarations stay untouched.

- [ ] Step 4: GREEN

Run: `uv run pytest tests/test_api_transcriber.py -v`
Expected output: all tests pass (`20 passed` — 17 pre-existing + 3 new).
PASTE the output.
Failure mode this catches: the QThread path sending no auth (run not
wired to api_key) or the extracted function regressing the empty-key case
(AC-12, AC-13).

- [ ] Step 5: Lint + type check

Run: `uv run ruff check src/core/api_transcriber.py && uv run mypy src/core/api_transcriber.py`
Expected output: no issues found.

- [ ] Step 6: Commit

```bash
git add src/core/api_transcriber.py tests/test_api_transcriber.py
git commit -m "feat(stt): send Bearer header and delegate run to transcribe

run() duplicated the POST body of transcribe(); delegating keeps the
auth-header behavior in one place (spec AC-12, AC-13)."
```
