# Task 4: Config keys rename + new keys + resolved_llm_url

**Files:**

- Modify: `src/utils/config_manager.py`
- Test: `tests/test_config.py`

**Interfaces:**

- Consumes: nothing new
- Produces: `STT_URL_DEFAULT` constant, renamed `stt_api_url` key, new
  `llm_api_url` / `stt_api_key` / `llm_api_key` keys, 4 new `ENV_MAP` rows,
  `ConfigManager.resolved_llm_url() -> str` — consumed by tasks 5 and 6.

BREAKING CHANGE (user-approved, spec `LEGACY_KEYS_DROPPED`): `api_url` and
`WHISPER_API_URL` are removed. No alias.

KNOWN TRANSIENT FAILURES (fixed by task 6): after this task, three tests in
`tests/test_settings_dialog.py` go red —
`test_settings_dialog_populates_from_config` (`_api_edit.text()` is `""`
because the dialog still reads the dead `api_url` key), and
`test_settings_dialog_cancel_does_not_save` plus
`test_settings_dialog_reject_button` (`saved["api_url"]` raises `KeyError`
because `DEFAULT_CONFIG` no longer carries the key). Task 6 fixes them. Do
NOT touch the dialog here.

- [ ] Step 1: Write the failing tests

APPEND these nine tests to `tests/test_config.py` (the file already imports
`patch` from `unittest.mock` and `ConfigManager`):

```python
def test_config_defaults_split_servers():
    cm = ConfigManager()
    assert cm.get("stt_api_url") == "http://localhost:8080"
    assert cm.get("llm_api_url") is None
    assert cm.get("stt_api_key") is None
    assert cm.get("llm_api_key") is None


def test_legacy_api_url_and_env_are_ignored(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text('{"api_url": "http://legacy:1"}')
    cm = ConfigManager()
    cm.config_dir = tmp_path
    cm.config_file = settings
    with patch.dict("os.environ", {"WHISPER_API_URL": "http://legacy-env"}):
        cm.config = cm.load_config()
    assert cm.get("stt_api_url") == "http://localhost:8080"
    assert cm.resolved_llm_url() == "http://localhost:8080"


def test_env_var_override_stt_api_url(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text('{"stt_api_url": "http://file:1"}')
    cm = ConfigManager()
    cm.config_dir = tmp_path
    cm.config_file = settings
    with patch.dict("os.environ", {"WHISPER_STT_API_URL": "http://env:9"}):
        cm.config = cm.load_config()
    assert cm.get("stt_api_url") == "http://env:9"


def test_env_var_override_llm_api_url(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text('{"llm_api_url": "http://file:1"}')
    cm = ConfigManager()
    cm.config_dir = tmp_path
    cm.config_file = settings
    with patch.dict("os.environ", {"WHISPER_LLM_API_URL": "http://env:9"}):
        cm.config = cm.load_config()
    assert cm.get("llm_api_url") == "http://env:9"


def test_resolved_llm_url_uses_llm_api_url():
    cm = ConfigManager()
    cm.config["stt_api_url"] = "http://a:1"
    cm.config["llm_api_url"] = "http://b:2"
    assert cm.resolved_llm_url() == "http://b:2"


def test_resolved_llm_url_falls_back_to_stt():
    cm = ConfigManager()
    cm.config["stt_api_url"] = "http://a:1"
    cm.config["llm_api_url"] = None
    assert cm.resolved_llm_url() == "http://a:1"


def test_resolved_llm_url_empty_llm_counts_as_unset():
    cm = ConfigManager()
    cm.config["stt_api_url"] = "http://a:1"
    cm.config["llm_api_url"] = ""
    assert cm.resolved_llm_url() == "http://a:1"


def test_resolved_llm_url_empty_stt_uses_default():
    cm = ConfigManager()
    cm.config["stt_api_url"] = ""
    cm.config["llm_api_url"] = None
    assert cm.resolved_llm_url() == "http://localhost:8080"


def test_env_var_override_api_keys():
    with patch.dict(
        "os.environ",
        {"WHISPER_STT_API_KEY": "sk-stt", "WHISPER_LLM_API_KEY": "sk-llm"},
    ):
        cm = ConfigManager()
    assert cm.get("stt_api_key") == "sk-stt"
    assert cm.get("llm_api_key") == "sk-llm"
```

Then UPDATE the five pre-existing tests that reference the dead key, exactly
as follows:

1. `test_config_defaults`: change line
   `assert cm.get("api_url") == "http://localhost:8080"` to
   `assert cm.get("stt_api_url") == "http://localhost:8080"`.
2. `test_config_save_load`: change
   `assert cm2.get("api_url") == "http://localhost:8080"` to
   `assert cm2.get("stt_api_url") == "http://localhost:8080"`.
3. `test_env_var_override_api_url` (the one using `WHISPER_API_URL`):
   replace the whole function with a skip marker — it is superseded by
   `test_legacy_api_url_and_env_are_ignored` and
   `test_env_var_override_stt_api_url`. Delete the function entirely.
4. `test_env_var_override_file_config`: replace both occurrences —
   `{"WHISPER_API_URL": "http://env-override.com"}` becomes
   `{"WHISPER_STT_API_URL": "http://env-override.com"}`,
   `cm.save_config({"api_url": "http://file-config.com"})` becomes
   `cm.save_config({"stt_api_url": "http://file-config.com"})`, and
   `assert cm2.get("api_url") == "http://env-override.com"` becomes
   `assert cm2.get("stt_api_url") == "http://env-override.com"`.
5. `test_config_load_config_file_not_readable`: change
   `cm.save_config({"api_url": "http://test.com"})` to
   `cm.save_config({"stt_api_url": "http://test.com"})`.

- [ ] Step 2: RED GATE

Run: `uv run pytest tests/test_config.py -v`
Expected output: the nine new tests AND the four updated pre-existing ones
that now reference the new schema (`test_config_defaults`,
`test_config_save_load`, `test_env_var_override_file_config`, and — if it
asserts the key — `test_config_load_config_file_not_readable`) FAIL with
`AssertionError` (get returns `None` for `stt_api_url`) or
`AttributeError: 'ConfigManager' object has no attribute 'resolved_llm_url'`.
The remaining pre-existing tests PASS.
PASTE the output.
PASTE the output.

- [ ] Step 3: Implement

In `src/utils/config_manager.py`:

1. Add `STT_URL_DEFAULT = "http://localhost:8080"` above `DEFAULT_CONFIG`.
2. Replace the whole `DEFAULT_CONFIG` and `ENV_MAP` blocks with the ones in
   interfaces.md § ConfigManager changes (rename `api_url` → `stt_api_url`,
   drop the `WHISPER_API_URL` row, add the four new rows and three new keys).
3. Add `resolved_llm_url` (interfaces.md § New method on ConfigManager) as
   a `ConfigManager` method, after `load_config`.

- [ ] Step 4: GREEN

Run: `uv run pytest tests/test_config.py -v`
Expected output: all tests pass (`18 passed` — 9 pre-existing remaining + 9
new). PASTE the output.
Failure mode this catches: an accidental alias keeping legacy `api_url`
alive (AC-2), a wrong env var name making overrides inert (AC-3, AC-5,
AC-9), or the fallback chain resolving wrongly (AC-6..AC-8).

- [ ] Step 5: REAL-ARTIFACT gate over the shipped schema

Run:

```bash
uv run python -c "from src.utils.config_manager import DEFAULT_CONFIG, ENV_MAP; assert 'api_url' not in DEFAULT_CONFIG and 'api_url' not in ENV_MAP; n = sum(k in DEFAULT_CONFIG for k in ['stt_api_url','llm_api_url','stt_api_key','llm_api_key']); assert n == 4, n; assert len(DEFAULT_CONFIG) == 13, len(DEFAULT_CONFIG); assert len(ENV_MAP) == 13, len(ENV_MAP); print('real-artifact OK:', n)"
```

Expected output: `real-artifact OK: 4`.
Failure mode this catches: a key silently missing from the shipped config
schema, or the rename leaving `api_url` behind.

- [ ] Step 6: Lint + type check

Run: `uv run ruff check src/utils/config_manager.py tests/test_config.py && uv run mypy src/utils/config_manager.py`
Expected output: no issues found.

- [ ] Step 7: Commit

```bash
git add src/utils/config_manager.py tests/test_config.py
git commit -m "feat(config)!: rename api_url to stt_api_url, add llm/key configs

New keys: llm_api_url, stt_api_key, llm_api_key (default None =
unset). resolved_llm_url() is the single fallback point: unset or
empty llm_api_url reuses the STT server.

BREAKING CHANGE: settings.json key api_url and env WHISPER_API_URL
are removed with no alias; rename them to stt_api_url /
WHISPER_STT_API_URL."
```
