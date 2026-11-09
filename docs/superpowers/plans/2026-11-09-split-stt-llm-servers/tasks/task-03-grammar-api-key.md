# Task 3: GrammarChecker api_key

**Files:**

- Modify: `src/core/grammar_checker.py`
- Test: `tests/test_grammar_checker.py`

**Interfaces:**

- Consumes: `auth_headers` from task 1 (`src.utils.auth_headers`)
- Produces: `GrammarChecker(api_url, model_name, api_key=None)` with
  `self.api_key: str | None`; `check_grammar(..., api_key=None)` — consumed
  by task 5 (cli wiring).

- [ ] Step 1: Write the failing tests

APPEND these three tests to `tests/test_grammar_checker.py` (the file
already imports `MagicMock`, `patch`, `pytest`, `QApplication`, and defines
the `mock_requests`, `app`, `mock_pyqt_signal` fixtures):

```python
def test_check_grammar_sends_bearer_header(mock_requests, app):
    from src.core.grammar_checker import check_grammar

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "fixed text"}}]
    }
    mock_requests.post.return_value = mock_response

    result = check_grammar(
        api_endpoint="http://localhost:8080/v1/chat/completions",
        model_name="gemma4-e4b-8b",
        text="raw text",
        api_key="sk-2",
    )

    assert result == "fixed text"
    _, kwargs = mock_requests.post.call_args
    assert kwargs["headers"] == {"Authorization": "Bearer sk-2"}


def test_check_grammar_no_key_sends_empty_headers(mock_requests, app):
    from src.core.grammar_checker import check_grammar

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "fixed text"}}]
    }
    mock_requests.post.return_value = mock_response

    result = check_grammar(
        api_endpoint="http://localhost:8080/v1/chat/completions",
        model_name="gemma4-e4b-8b",
        text="raw text",
        api_key=None,
    )

    assert result == "fixed text"
    _, kwargs = mock_requests.post.call_args
    assert kwargs["headers"] == {}


def test_grammarchecker_run_passes_api_key(mock_pyqt_signal, mock_requests, app):
    from src.core.grammar_checker import GrammarChecker

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "fixed text"}}]
    }
    mock_requests.post.return_value = mock_response

    checker = GrammarChecker("http://localhost:8080", "gemma4-e4b-8b", "k2")
    checker.set_text("raw text")
    results = []
    checker.finished.connect(results.append)
    checker.run()

    assert results == ["fixed text"]
    _, kwargs = mock_requests.post.call_args
    assert kwargs["headers"] == {"Authorization": "Bearer k2"}
```

- [ ] Step 2: RED GATE

Run: `uv run pytest tests/test_grammar_checker.py -v`
Expected output: the three new tests FAIL — the first two with
`TypeError: check_grammar() got an unexpected keyword argument 'api_key'`,
the third with `TypeError: __init__() takes 3 positional arguments but 4
were given`. All pre-existing tests still PASS.
PASTE the output.

- [ ] Step 3: Implement

In `src/core/grammar_checker.py`:

1. Add the import `from src.utils.auth_headers import auth_headers`
   (interfaces.md § GrammarChecker changes).
2. Replace `check_grammar` with the block in interfaces.md § Full
   replacement `check_grammar` — only the signature and the
   `requests.post(...)` call change; the system prompt and payload dict
   stay byte-for-byte identical.
3. Replace `GrammarChecker.__init__` and `run` with the blocks in
   interfaces.md.

- [ ] Step 4: GREEN

Run: `uv run pytest tests/test_grammar_checker.py -v`
Expected output: all tests pass (`15 passed` — 12 pre-existing + 3 new).
PASTE the output.
Failure mode this catches: the LLM server receiving a request without its
Bearer token (401 at runtime), or an `Authorization` header leaking onto
the no-auth path (AC-14, `EMPTY_KEY_MEANS_NO_AUTH`).

- [ ] Step 5: Lint + type check

Run: `uv run ruff check src/core/grammar_checker.py && uv run mypy src/core/grammar_checker.py`
Expected output: no issues found.

- [ ] Step 6: Commit

```bash
git add src/core/grammar_checker.py tests/test_grammar_checker.py
git commit -m "feat(llm): send Bearer header on grammar check requests

Per-server key for the chat endpoint; empty key keeps local no-auth
servers working (spec AC-14)."
```
