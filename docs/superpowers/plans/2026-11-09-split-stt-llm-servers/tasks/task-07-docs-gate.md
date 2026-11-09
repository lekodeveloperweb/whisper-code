# Task 7: Docs + closing gate

**Files:**

- Modify: `AGENTS.md`, `CLAUDE.md`, `docs/configuration.md`,
  `docs/INSTALLATION.md`, `docs/quickstart.md`
- Test: none (docs-only; the gate below re-runs everything)

**Interfaces:**

- Consumes: the final shipped schema from tasks 4-6.
- Produces: nothing.

`docs/RELEASE-v1.0.0.md` is a historical release note — do NOT touch it.

- [x] Step 1: Update the agent instruction files

In BOTH `AGENTS.md` and `CLAUDE.md` (identical notes section), replace the
two config lines:

```
- Config keys: `api_url`, `model_name`, `hotkey`, `auto_insert`, `sample_rate`, `use_grammar_check`, `grammar_model`.
- Env var overrides: `WHISPER_API_URL`, `WHISPER_MODEL_NAME`, `WHISPER_HOTKEY`, `WHISPER_AUTO_INSERT`, `WHISPER_SAMPLE_RATE`, `WHISPER_GRAMMAR_CHECK`, `WHISPER_GRAMMAR_MODEL`.
```

with:

```
- Config keys: `stt_api_url`, `stt_api_key`, `llm_api_url`, `llm_api_key`, `model_name`, `model_quality`, `hotkey`, `auto_insert`, `sample_rate`, `use_grammar_check`, `grammar_model`.
- Env var overrides: `WHISPER_STT_API_URL`, `WHISPER_STT_API_KEY`, `WHISPER_LLM_API_URL`, `WHISPER_LLM_API_KEY`, `WHISPER_MODEL_NAME`, `WHISPER_MODEL_QUALITY`, `WHISPER_HOTKEY`, `WHISPER_AUTO_INSERT`, `WHISPER_SAMPLE_RATE`, `WHISPER_GRAMMAR_CHECK`, `WHISPER_GRAMMAR_MODEL`, `WHISPER_SILENCE_THRESHOLD`, `WHISPER_VOICE_COMMANDS`.
- `llm_api_url` unset/empty falls back to `stt_api_url` (single source of truth: `ConfigManager.resolved_llm_url()`). Empty keys send no Authorization header. BREAKING (v1.1): `api_url`/`WHISPER_API_URL` were removed — rename to `stt_api_url`/`WHISPER_STT_API_URL`.
```

- [x] Step 2: Update `docs/configuration.md`

Read the file, then rewrite its config example and tables to the shipped
schema: JSON example gains `"stt_api_url": "http://localhost:8080"`,
`"llm_api_url": null`, `"stt_api_key": null`, `"llm_api_key": null` and
loses `"api_url"`; the keys table gets rows for the four new keys (LLM URL
row notes the fallback; key rows note Bearer auth, empty ⇒ no header); the
env table replaces the `WHISPER_API_URL` row with
`WHISPER_STT_API_URL`, `WHISPER_STT_API_KEY`, `WHISPER_LLM_API_URL`,
`WHISPER_LLM_API_KEY`. Keep the file's existing table style.

- [x] Step 3: Update user-facing examples

In `docs/INSTALLATION.md` and `docs/quickstart.md`, replace the example
`"api_url": "http://localhost:8080"` with `"stt_api_url":
"http://localhost:8080"` and rename the field description
(`**api_url**: ...` → `**stt_api_url**: ...`). Add no new sections.

- [x] Step 4: CLOSING GATE — whole-suite verification

Run each of these, in order, and PASTE every output:

```bash
uv run pytest tests/ -q
uv run ruff check .
uv run mypy src/
```

Expected: pytest reports all tests pass with ZERO failures (this is the
first point where the KNOWN TRANSIENT FAILURE from task 4 is required to
be gone — if `tests/test_settings_dialog.py` is red, a previous task was
incomplete; fix there, not here). ruff and mypy report no issues.

- [x] Step 5: REAL-ARTIFACT gate — end-to-end resolution

Run:

```bash
uv run python - <<'PY'
from unittest.mock import patch
from src.utils.config_manager import ConfigManager

with patch.dict("os.environ", {
    "WHISPER_STT_API_URL": "http://stt.env:1",
    "WHISPER_STT_API_KEY": "sk-stt",
    "WHISPER_LLM_API_URL": "http://llm.env:2",
}, clear=False):
    cm = ConfigManager()
    cm.load_config()
    assert cm.get("stt_api_url") == "http://stt.env:1", cm.get("stt_api_url")
    assert cm.get("stt_api_key") == "sk-stt"
    assert cm.resolved_llm_url() == "http://llm.env:2"
print("real-artifact OK")
PY
```

Expected output: `real-artifact OK`.
Failure mode this catches: env-var typos or merge-order regressions that
unit mocks would miss, verified through the real settings file path.

- [x] Step 6: Commit

```bash
git add AGENTS.md CLAUDE.md docs/configuration.md docs/INSTALLATION.md docs/quickstart.md
git commit -m "docs: document split STT/LLM config keys and env overrides

api_url/WHISPER_API_URL replaced by stt_api_url + per-server keys;
notes the llm_api_url -> stt_api_url fallback (spec documentation
section)."
```
