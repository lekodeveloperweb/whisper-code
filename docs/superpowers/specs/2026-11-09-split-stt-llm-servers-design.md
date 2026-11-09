# Split STT and LLM Servers Design

**Date:** 2026-11-09 **Status:** Draft (rev 2 — hard rename of `api_url` to
`stt_api_url`, no legacy alias, per user decision)

## Overview

Whisper-Code today points both the STT path (`APITranscriber`) and the
grammar-refinement path (`GrammarChecker`) at one `api_url`, with no API-key
support. This design replaces that with four config keys — `stt_api_url`,
`stt_api_key`, `llm_api_url`, `llm_api_key` — so the two paths target
OpenAI-compatible (chat) and Whisper-compatible (transcription) servers
independently, each with its own optional Bearer token. The rename is a hard
cut: `api_url` and `WHISPER_API_URL` are removed; an unset `llm_api_url`
still falls back to `stt_api_url`.

## Design

### Config keys (`src/utils/config_manager.py`)

`DEFAULT_CONFIG`: rename `api_url` → `stt_api_url` (same value
`"http://localhost:8080"`); add three keys defaulting to `None` (= "unset"):

```python
"stt_api_url": "http://localhost:8080",  # Whisper-compatible /v1/audio server
"llm_api_url": None,   # OpenAI-compatible /v1/chat server; None/"" ⇒ stt_api_url
"stt_api_key": None,   # Bearer token for STT server; None/"" ⇒ no header
"llm_api_key": None,   # Bearer token for LLM server; None/"" ⇒ no header
```

`ENV_MAP`: remove the `api_url` entry entirely; add four `str` rows:

```python
"stt_api_url": ("WHISPER_STT_API_URL", str),
"llm_api_url": ("WHISPER_LLM_API_URL", str),
"stt_api_key": ("WHISPER_STT_API_KEY", str),
"llm_api_key": ("WHISPER_LLM_API_KEY", str),
```

BREAKING CHANGE (user-approved): a `settings.json` that still contains
`api_url`, or an environment that still sets `WHISPER_API_URL`, has **no
effect** — the merge just carries the unknown `api_url` key through
unread. Migration is: rename the key.

The existing `load_config` empty-string rule (`env_value != ""`) stays: an
empty env value never overrides.

`ConfigManager` gains one method — the single source of truth for the
fallback rule:

```python
def resolved_llm_url(self) -> str:
    """Base URL for the chat/completions server.

    Returns llm_api_url when it is a non-empty string, else the STT
    stt_api_url (or STT_URL_DEFAULT when that too is empty).

    >>> ConfigManager().resolved_llm_url()  # llm_api_url unset
    'http://localhost:8080'
    """
```

WHY the fallback lives here and not in cli/dialog: three call sites
(`_make_grammar_checker`, `_apply_grammar_config`, `_log_startup`) need the
same rule; duplicating it invites drift.

### Shared auth helper (`src/utils/auth_headers.py`, new file)

```python
def auth_headers(api_key: str | None) -> dict[str, str]:
    """Bearer header for OpenAI-compatible endpoints; {} when no key."""
```

Returns `{"Authorization": "Bearer " + api_key}` for a non-empty string,
`{}` for `None` or empty. It lives in `src/utils/` so both `core/`
components import the shared helper instead of one importing from the other
(no core→core dependency; AGENTS.md "extract shared logic").

### APITranscriber (`src/core/api_transcriber.py`)

- `__init__(self, api_url: str, model_name: str, api_key: str | None = None)`;
  stores `self.api_key: str | None`.
- Module-level `transcribe(...)` gains a keyword arg
  `api_key: str | None = None` and passes `headers=auth_headers(api_key)` to
  `requests.post`.
- `QThread.run()` is refactored to delegate to `transcribe()` with the Qt
  signal emitters as callbacks, mirroring `GrammarChecker.run()` — removing
  the duplicated POST body (AGENTS.md no-duplication rule) so the header
  behavior lives in exactly one place. `self.last_result` is set from
  `transcribe()`'s return value.
- The multipart body and timeout stay untouched — the only wire change is
  the header. (WIRE FORMAT note: nothing is appended to any model message
  `content`; auth travels in HTTP headers, so no custom content shape is
  introduced.)

### GrammarChecker (`src/core/grammar_checker.py`)

- `__init__(self, api_url: str, model_name: str, api_key: str | None = None)`;
  stores `self.api_key: str | None`.
- `check_grammar(...)` gains `api_key: str | None = None` and passes
  `headers=auth_headers(api_key)` to `requests.post`.

### App wiring (`src/whisper_code/cli.py`)

- `_make_transcriber()` → `APITranscriber(stt_api_url, resolved_model, stt_api_key)`
  where the URL/key come from `config.get("stt_api_url")` / `config.get("stt_api_key")`.
- `_make_grammar_checker()` →
  `GrammarChecker(config.resolved_llm_url(), grammar_model, config.get("llm_api_key"))`.
- `_apply_api_url()` is renamed `_apply_stt_url()` and additionally sets
  `self.transcriber.api_key` when the stored key differs from config.
- `_apply_grammar_config()` builds its endpoint from
  `config.resolved_llm_url()` and additionally sets
  `self.grammar_checker.api_key` when changed.
- `_log_startup()` logs both resolved URLs and both models; it never logs
  key values. Keys are never interpolated into any log line, toast, or
  error message.

Keys are independent: `stt_api_key` is only ever read into
`transcriber.api_key`, `llm_api_key` only into `grammar_checker.api_key`.

### Settings dialog (`src/gui/settings_dialog.py`)

Regrouped into two server groups plus existing preferences:

- **STT Server**: `&API URL:` (existing `_api_edit`, now bound to
  `stt_api_url`), `A&PI Key:` (new `_stt_key_edit`), `&Model Name:`
  (existing), `&Model Quality:` (moved from Preferences).
- **LLM Server**: `API &URL:` (new `_llm_api_edit`, bound to `llm_api_url`),
  `API Ke&y:` (new `_llm_key_edit`), `&Grammar Model:` (moved from
  Preferences), `Enable grammar checking` (moved from Preferences).
- **Preferences**: auto-insert, sample rate, silence threshold, voice
  commands (hotkey group unchanged).

Both key fields use `QLineEdit.EchoMode.Password`. `_populate_widgets`
loads the four keys (the LLM URL field shows the raw `llm_api_url` value —
an empty string when it is `None`, which the fallback rule treats as
unset); `_apply_config` writes `stt_api_url`, `llm_api_url` (empty text →
`""`), `stt_api_key`, `llm_api_key`. All new widgets are appended to
`_widget_refs` (the PySide6 GC workaround already in place).

### Documentation (non-behavioral, no AC)

`AGENTS.md`/`CLAUDE.md` and `docs/configuration.md` config-key and env-var
lists are updated: `api_url`/`WHISPER_API_URL` removed, the four new keys
and four env names listed. Docs-only; not exercised by ACs by design.

## Constants

- `AUTH_HEADER_FORMAT = "Authorization: Bearer {key}"  # wire format for both servers, exercised by AC-10`
- `EMPTY_KEY_MEANS_NO_AUTH = None | "" ⇒ {}  # keeps local no-auth servers working, exercised by AC-11, AC-13, AC-14`
- `STT_URL_DEFAULT = "http://localhost:8080"  # pre-existing default under its new key name, exercised by AC-1, AC-2, AC-8`
- `LLM_URL_FALLBACK = stt_api_url  # unset/empty llm_api_url reuses the STT server, exercised by AC-6, AC-7`
- `LEGACY_KEYS_DROPPED = api_url | WHISPER_API_URL  # hard rename, no alias, exercised by AC-2`
- `NEW_CONFIG_DEFAULTS = llm_api_url | stt_api_key | llm_api_key = None  # "unset" sentinel, exercised by AC-1`
- `ENV_STT_API_URL = WHISPER_STT_API_URL  # env override name, exercised by AC-3`
- `ENV_LLM_API_URL = WHISPER_LLM_API_URL  # env override name, exercised by AC-5`
- `ENV_STT_API_KEY = WHISPER_STT_API_KEY  # env override name, exercised by AC-9`
- `ENV_LLM_API_KEY = WHISPER_LLM_API_KEY  # env override name, exercised by AC-9`

## Acceptance Criteria

1. `load_config with no settings.json and no env vars ⇒ config["stt_api_url"] == "http://localhost:8080" and config["llm_api_url"] is None and config["stt_api_key"] is None and config["llm_api_key"] is None`
2. `legacy settings.json {"api_url":"http://legacy:1"} plus env WHISPER_API_URL="http://legacy-env" ⇒ config["stt_api_url"] == "http://localhost:8080" and resolved_llm_url() == "http://localhost:8080"` (hard rename: legacy names have no effect)
3. `env WHISPER_STT_API_URL="http://env:9" over settings.json {"stt_api_url":"http://file:1"} ⇒ config["stt_api_url"] == "http://env:9"`
4. `settings.json {"stt_api_url":"http://a:1","llm_api_url":"http://b:2"} ⇒ resolved_llm_url() == "http://b:2"`
5. `env WHISPER_LLM_API_URL="http://env:9" over settings.json {"llm_api_url":"http://file:1"} ⇒ config["llm_api_url"] == "http://env:9"`
6. `settings.json {"stt_api_url":"http://a:1"} with llm_api_url absent ⇒ resolved_llm_url() == "http://a:1"`
7. `settings.json {"stt_api_url":"http://a:1","llm_api_url":""} ⇒ resolved_llm_url() == "http://a:1"` (empty counts as unset)
8. `settings.json {"stt_api_url":""} with llm_api_url absent ⇒ resolved_llm_url() == "http://localhost:8080"`
9. `env WHISPER_STT_API_KEY="sk-stt" ⇒ config["stt_api_key"] == "sk-stt"` and `env WHISPER_LLM_API_KEY="sk-llm" ⇒ config["llm_api_key"] == "sk-llm"`
10. `auth_headers("sk-abc") ⇒ {"Authorization": "Bearer sk-abc"}` (exact header name and scheme)
11. `auth_headers(None) ⇒ {}` and `auth_headers("") ⇒ {}`
12. `transcribe(endpoint, model, audio, api_key="sk-1") ⇒ requests.post called with headers={"Authorization": "Bearer sk-1"}` (fake requests, not network)
13. `transcribe(endpoint, model, audio, api_key=None) ⇒ requests.post called with headers={}`
14. `check_grammar(endpoint, model, text, api_key="sk-2") ⇒ post headers == {"Authorization": "Bearer sk-2"}`; `check_grammar(..., api_key=None) ⇒ post headers == {}`
15. `WhisperCodeApp wiring with stt_api_key="k1", llm_api_key unset, llm_api_url unset, stt_api_url="http://a:1" ⇒ transcriber.api_key == "k1" and grammar_checker.api_endpoint == "http://a:1/v1/chat/completions" and grammar_checker.api_key is None` (independence + fallback through the app)
16. `save_config({"llm_api_url": "http://new:2"}) then _on_settings_saved/_apply_settings ⇒ grammar_checker.api_endpoint == "http://new:2/v1/chat/completions"` (hot-reload of the LLM URL)
17. `save_config({"stt_api_key": "k9", "llm_api_key": "k8"}) then _apply_settings ⇒ transcriber.api_key == "k9" and grammar_checker.api_key == "k8"`
18. `SettingsDialog populated with stt_api_url="http://a:1" and stt_api_key="sk-1" ⇒ STT URL field text == "http://a:1", STT key field text == "sk-1", key field echoMode == QLineEdit.EchoMode.Password`; `_apply_config() ⇒ returned dict contains keys "stt_api_url", "llm_api_url", "stt_api_key", "llm_api_key"`
19. `dialog accept with _llm_api_edit text "http://x:9" ⇒ settings.json written to disk contains "llm_api_url": "http://x:9"`
20. `run _log_startup with stt_api_url="http://a:1", llm_api_url="http://b:2", stt_api_key="secret-stt", llm_api_key="secret-llm" ⇒ captured log records contain "http://a:1" and "http://b:2" but neither "secret-stt" nor "secret-llm"`
