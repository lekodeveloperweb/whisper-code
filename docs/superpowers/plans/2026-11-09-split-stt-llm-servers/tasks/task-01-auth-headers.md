# Task 1: auth_headers helper

**Files:**

- Create: `src/utils/auth_headers.py`
- Test: `tests/test_auth_headers.py`

**Interfaces:**

- Consumes: nothing (first task)
- Produces: `auth_headers(api_key: str | None) -> dict[str, str]` from
  `src.utils.auth_headers` — used by tasks 2 and 3.

- [x] Step 1: Write the failing test

Create `tests/test_auth_headers.py` with exactly this code:

```python
"""Tests for the shared Bearer header builder (spec AC-10, AC-11)."""

from src.utils.auth_headers import auth_headers


def test_auth_headers_returns_bearer_for_key():
    assert auth_headers("sk-abc") == {"Authorization": "Bearer sk-abc"}


def test_auth_headers_empty_for_none():
    assert auth_headers(None) == {}


def test_auth_headers_empty_for_empty_string():
    assert auth_headers("") == {}
```

- [x] Step 2: RED GATE — run it, expect failure

Run: `uv run pytest tests/test_auth_headers.py -v`
Expected output: collection ERROR with
`ModuleNotFoundError: No module named 'src.utils.auth_headers'`
PASTE the output. A test that passes before the module exists is VACUOUS.

- [x] Step 3: Implement

Create `src/utils/auth_headers.py` with the complete code from
`interfaces.md` § auth_headers. Do not re-type from memory — copy the block.

- [x] Step 4: GREEN — run again

Run: `uv run pytest tests/test_auth_headers.py -v`
Expected output: `3 passed`
PASTE the output.
Failure mode this catches: a wrong header name or scheme (AC-10) or an
`Authorization` header sent for empty keys, which would break local no-auth
servers (AC-11 / `EMPTY_KEY_MEANS_NO_AUTH`).

- [x] Step 5: Format + type check this module

Run: `uv run ruff check src/utils/auth_headers.py tests/test_auth_headers.py && uv run ruff format --check src/utils/auth_headers.py tests/test_auth_headers.py && uv run mypy src/utils/auth_headers.py`
Expected output: no issues found on all three commands.

- [x] Step 6: Commit

```bash
git add src/utils/auth_headers.py tests/test_auth_headers.py
git commit -m "feat(utils): add Bearer auth header helper

Empty/absent keys yield {} so local no-auth servers keep working
(spec 2026-11-09-split-stt-llm-servers, AC-10, AC-11)."
```
