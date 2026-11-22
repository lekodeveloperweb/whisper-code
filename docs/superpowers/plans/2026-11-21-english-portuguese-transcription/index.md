**Spec: docs/superpowers/specs/2026-11-21-english-portuguese-transcription-design.md**

# English and Portuguese Transcription Implementation Plan

**Status:** Approved for execution. The source spec and plan have been approved; implementation does not include commit authorization.

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

## Repository Checks

The application and tests are Python; deployment artifacts are Kubernetes YAML; project guidance and user-facing docs are Markdown. `uv` is the package manager (`uv.lock`); pytest, mypy, and Ruff are declared in `pyproject.toml`. The repository has Makefile targets for lint, typecheck, and tests. No workflow files were found under `.github` or `.gitea`.

| Check | Exact command | What it verifies | Applicability / limitation |
| --- | --- | --- | --- |
| Test suite | `uv run pytest tests/ -v --cov=src/ --cov-report=term-missing` | Unit and integration behavior across `src/` | Applicable; baseline isolated rerun passed 265 tests. One initial parallel run had a non-reproducible failure/Qt crash; see Plan Preflight. |
| Type check | `uv run mypy src/` | Strict source annotations and return types | Applicable; baseline: `No issues found`. |
| Lint | `uv run ruff check .` | Configured Ruff lint rules across repository files | Applicable; baseline: `No issues found`. |
| Format | `uv run ruff format --check .` | Python formatting, including Python code blocks Ruff discovers in Markdown | Applicable; baseline already reports four unrelated existing Markdown files. Run this check and separately check changed Python files; do not format unrelated baseline files. |
| Real artifacts | `kubectl kustomize /Users/lekodeveloperweb/workspace/ldw/projects/devops/ldw.solutions.vps.settings/K3/speaches` plus the Task 5 assertions | Kustomize rendering and exact model/resource preservation in the actual sibling deployment; documentation inventory covers the five app docs plus K3 README | Applicable. Baseline render produces 8 Kubernetes documents and contains the old model reference once. `kubectl` is installed; `yq` and PyYAML are unavailable. Live rollout requires operator cluster/API credentials. |
| Stub / re-type | `python3 - <<'PY'` (complete script under Interface and Plan Self-Review) | Python snippets parse; interface bodies are complete; task files refer to interfaces instead of duplicating implementation | Applicable. No Markdown-aware stub/re-type checker is configured, so the final check includes a documented manual comparison. |

## Plan Preflight

### Baseline commands and observed results

| Baseline check | Exact command | Actual result/output | Environmental failure or limitation |
| --- | --- | --- | --- |
| Full tests, first attempt | `uv run pytest tests/ -v --cov=src/ --cov-report=term-missing` (run concurrently with independent lint/type checks) | 265 collected; progress showed one failure in `tests/test_text_injector.py`, then a fatal segmentation fault in `tests/test_tray_menu.py::test_activation_reasons_show_menu_below_icon` at line 149; process exit 139 | Not reproducible. No root cause established; do not attribute it to this feature. |
| Failure isolation | `uv run pytest tests/test_text_injector.py -vv` | `13 passed in 1.65s` | None. |
| Suite without tray-menu tests | `uv run pytest tests/ -v --ignore=tests/test_tray_menu.py` | `250 passed in 5.47s` | Tray-menu tests excluded only for isolation. |
| Full tests, fail-fast rerun | `uv run pytest tests/ -v --cov=src/ --cov-report=term-missing -x` | `265 passed in 5.77s` | None. |
| Full tests, sequential rerun | `uv run pytest tests/ -v --cov=src/ --cov-report=term-missing` | `265 passed in 5.79s` | None. This is the recorded passing baseline. |
| Type check | `uv run mypy src/` | `Success: no issues found in 28 source files` | None. |
| Lint | `uv run ruff check .` | `All checks passed!` | None. |
| Format | `uv run ruff format --check .` | 4 files would be reformatted: `docs/PACKAGING.md`, `docs/api-reference.md`, `docs/superpowers/plans/2026-11-09-split-stt-llm-servers/interfaces.md`, and `docs/superpowers/plans/2026-11-09-split-stt-llm-servers/tasks/task-03-grammar-api-key.md`; 70 files were already formatted. | Existing baseline findings; leave those files untouched. |
| K3 artifact render | `kubectl kustomize /Users/lekodeveloperweb/workspace/ldw/projects/devops/ldw.solutions.vps.settings/K3/speaches` | Rendered 8 Kubernetes documents; rendered model value `Systran/faster-distil-whisper-small.en` appears once. | `yq` and PyYAML are unavailable; `kubectl kustomize` is the real manifest parser. |
| K3 tree state | `git -C /Users/lekodeveloperweb/workspace/ldw/projects/devops/ldw.solutions.vps.settings status --short` | No output; sibling repository is clean. | None. |
| CI inventory | `find .github .gitea -maxdepth 4 -type f` | No files returned. | No checked-in workflow config found in those locations. |
| Live cluster | `kubectl rollout status deployment/speaches -n speaches --timeout=10m` | Not run during preflight. | Requires the operator's current Kubernetes context; the authenticated model-list check additionally requires `WHISPER_STT_API_URL` and `WHISPER_STT_API_KEY`. Run after deployment. |

### Task prerequisites and execution order

| Task | Depends on | Prerequisite provided | Gates and first runnable boundary |
| --- | --- | --- | --- |
| Task 1 — Discovery and config | None | Canonical language/model defaults, environment mapping, and `/v1/models` discovery helper | Discovery/config tests run at Task 1 Step 2 (RED) and Step 4 (GREEN). |
| Task 2 — Settings language UI | Task 1 | Capability-backed choices, unsupported-selection rules, retryable-error state, and persistence | Settings tests run at Task 2 Step 2 and Step 4; they require Task 1's helper. |
| Task 3 — Refresh hardening | Task 2 | Refresh uses current form values; asynchronous request remains off the Qt event loop; errors are secret-safe | Settings refresh/responsiveness tests run at Task 3 Step 2 and Step 4. |
| Task 4 — Transcription and language preservation | Tasks 1-3 | Selected language reaches the multipart request and hot reload; grammar refinement preserves language; raw transcript path is covered | API, CLI, grammar, and integration tests run at Task 4 Step 2 and Step 4. |
| Task 5 — K3, docs, and final gates | Tasks 1-4 | Multilingual deployment/docs plus all app components and tests | Real Kustomize artifact gate runs at Task 5 Steps 2/4; full tests, type check, lint, format, and post-rollout checks run only at Task 5 Step 4. |

The full integration, mypy, Ruff, and real-artifact gates are deliberately placed after all tasks that provide their components. The K3 rollout/API check is a post-deployment operator gate, not a baseline pass.

## Global Constraints

- `APP_LANGUAGE_OPTIONS = (("en", "English"), ("pt", "Portuguese"))  # exposes only the two requested input languages, exercised by AC-1, AC-2, AC-4, and AC-5`
- `DEFAULT_TRANSCRIPTION_LANGUAGE = "en"  # matches the current Speaches default, exercised by AC-15, AC-22, and AC-25`
- `LANGUAGE_CONFIG_KEY = "transcription_language"  # persisted setting name, exercised by AC-15, AC-16, and AC-19`
- `LANGUAGE_ENV_VAR = "WHISPER_TRANSCRIPTION_LANGUAGE"  # environment override name, exercised by AC-16`
- `SPEACHES_MODELS_PATH = "/v1/models"  # installed-model capability source, exercised by AC-1, AC-7 through AC-14, and AC-26 through AC-28`
- `SPEACHES_MODELS_RESPONSE_SHAPE = {"data": [{"id": str, "task"?: str, "language": list[str]}]}  # model-list capability schema; task is optional in Speaches 0.7.0`
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

## Interface and Plan Self-Review

The implementation snippets are centralized in `interfaces.md`; task files contain test code and edit/run instructions. The following check was run from the repository root:

```bash
python3 - <<'PY'
from pathlib import Path
import ast, re, sys
root = Path("docs/superpowers/plans/2026-11-21-english-portuguese-transcription")
spec = Path("docs/superpowers/specs/2026-11-21-english-portuguese-transcription-design.md").read_text()
index = (root / "index.md").read_text()
def section(text, start, end):
    return text.split(start, 1)[1].split(end, 1)[0]
spec_ac = [line for line in section(spec, "## Acceptance Criteria", "## Constants").splitlines() if re.match(r"^\d+\. ", line)]
index_ac = [line for line in section(index, "## Acceptance Criteria", "## Repository Checks").splitlines() if re.match(r"^\d+\. ", line)]
spec_constraints = [line[2:] for line in section(spec, "## Constants", "## Acceptance Criteria").splitlines() if line.startswith("- ")]
index_constraints = [line[2:] for line in section(index, "## Global Constraints", "## Interface and Plan Self-Review").splitlines() if line.startswith("- ")]
coverage_section = re.search(r"(?ms)^## Spec Coverage\n(.*?)^## Constraint Coverage\n", index).group(1)
coverage = [line for line in coverage_section.splitlines() if re.match(r"^\| \d+\. ", line)]
assert spec_ac == index_ac and spec_constraints == index_constraints and len(coverage) == len(spec_ac)
paths = [root / "interfaces.md", *sorted((root / "tasks").glob("*.md"))]
errors, fences = [], 0
for path in paths:
    text = path.read_text()
    for match in re.finditer(r"^```python\s*\n(.*?)^```\s*$", text, re.M | re.S):
        try:
            tree = ast.parse(match.group(1))
        except SyntaxError as exc:
            errors.append(f"{path}: syntax error: {exc.msg}")
            continue
        fences += 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and len(node.body) == 1:
                body = node.body[0]
                if isinstance(body, ast.Pass) or (isinstance(body, ast.Expr) and isinstance(body.value, ast.Constant) and (body.value.value is Ellipsis or isinstance(body.value.value, str))):
                    errors.append(f"{path}: stub-only function {node.name}")
interface_text = (root / "interfaces.md").read_text()
task_text = "\n".join(path.read_text() for path in sorted((root / "tasks").glob("*.md")))
symbols = ["APP_LANGUAGE_OPTIONS", "DEFAULT_TRANSCRIPTION_LANGUAGE", "LANGUAGE_CONFIG_KEY", "LANGUAGE_ENV_VAR", "MULTILINGUAL_STT_MODEL_ID", "SPEACHES_MODELS_PATH", "SPEACHES_MODELS_RESPONSE_SHAPE", "SPEACHES_ASR_TASK", "LANGUAGE_REQUEST_FIELD", "LANGUAGE_DISCOVERY_TIMEOUT_SECONDS", "SPEACHES_IMAGE_VERSION", "K3_DEFAULT_LANGUAGE", "K3_INFERENCE_DEVICE", "K3_COMPUTE_TYPE", "K3_CPU_THREADS", "K3_MEMORY_LIMIT_GIB", "SpeachesModelRecord", "SpeachesModelsResponse", "LanguageDiscoveryError", "fetch_model_languages", "_LanguageDiscoveryWorker", "transcription_form_data", "GRAMMAR_LANGUAGE_PRESERVATION_INSTRUCTION"]
for name in symbols:
    if name not in interface_text or name not in task_text:
        errors.append(f"missing interface/task reference: {name}")
for name in ["fetch_model_languages", "_LanguageDiscoveryWorker", "transcription_form_data"]:
    if re.search(rf"(?m)^(?:async\s+def|def|class)\s+{re.escape(name)}\b", task_text):
        errors.append(f"task redefines interface symbol: {name}")
names = sorted(set(re.findall(r"`(test_[a-zA-Z0-9_]+)`", index)))
missing_tests = [name for name in names if name not in task_text]
if missing_tests:
    errors.append(f"missing named tests: {missing_tests}")
if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"Approved AC exact-copy: {len(spec_ac)}/{len(index_ac)}; constraints exact-copy: {len(spec_constraints)}/{len(index_constraints)}; coverage rows: {len(coverage)}.")
print(f"AST parsed {fences} Python fences; no syntax errors or stub-only functions.")
print(f"All {len(symbols)} interface symbols and {len(names)} named tests are referenced; no duplicate production definitions.")
PY
```

Observed output:

```text
Approved AC exact-copy: 29/29; constraints exact-copy: 17/17; coverage rows: 29.
AST parsed 14 Python fences; no syntax errors or stub-only functions.
All 23 interface symbols and 21 named tests are referenced; no duplicate production definitions.
```

A separate exact-order check confirmed 17 constraint-coverage rows with the same constraint text/value as the approved constants.

Interface locations: shared application constants `interfaces.md:10-17`; discovery constants, schema, and helper `interfaces.md:53-125`; Qt worker `interfaces.md:139-169`; STT form contract `interfaces.md:174-184`; grammar instruction `interfaces.md:198-199`; response/K3 invariants `interfaces.md:201-213`. Task interface references are `task-01:7`, `task-02:10-13`, `task-03:10-13`, `task-04:15-18`, and `task-05:15-18`. Every task file has one task heading and is 150 lines or fewer (147, 130, 109, 113, and 94 lines).

Formatting and hygiene checks: the targeted Ruff formatter command over `index.md`, `interfaces.md`, and `tasks/*.md` reported `7 files already formatted`; `uv run ruff check` over those Markdown paths reported `No issues found` with the expected `No Python files found` warning. The full `uv run ruff format --check .` reported only the four documented pre-existing Markdown failures and `77 files already formatted`. The unfinished-marker scan and trailing-whitespace scan returned no matches. The baseline Python test suite and source checks are recorded under Plan Preflight; no implementation or feature test was run during planning.

## Spec Coverage

| AC (INPUT ⇒ EXPECTED, verbatim from approved spec) | Task | Verify step |
| --- | --- | --- |
| 1. `GET /v1/models` returns three records: `{"id":"Systran/faster-whisper-small","task":"automatic-speech-recognition","language":["en","pt","es"]}`, `{"id":"other/asr","task":"automatic-speech-recognition","language":["pt"]}`, and `{"id":"kokoro/tts","task":"text-to-speech","language":["en","pt"]}` ⇒ `fetch_model_languages` returns exactly `["en", "pt"]` for `Systran/faster-whisper-small`. | Task 1 | Step 4 — `test_filters_exact_asr_model_and_app_languages` |
| 2. The configured ASR model advertises languages `["en", "pt", "es"]` ⇒ the Settings combo contains exactly two choices with item data `en`, `pt` and labels English, Portuguese; it contains no Spanish or Auto-detect choice. | Task 2 | Step 4 — `test_language_combo_has_only_english_and_portuguese` |
| 3. The configured model advertises languages `["en", "pt"]` and the saved language is `pt` ⇒ the combo's current item data is `pt`. | Task 2 | Step 4 — `test_language_combo_has_only_english_and_portuguese` |
| 4. The configured ASR model advertises only `["en"]` and the saved language is `pt` ⇒ the dialog marks Portuguese unavailable and keeps OK disabled until English is selected. | Task 2 | Step 4 — `test_unsupported_saved_language_requires_valid_choice` |
| 5. The configured ASR model advertises only `["es"]` and the saved language is `en` ⇒ Settings reports that the model supports neither app language and keeps OK disabled. | Task 2 | Step 4 — `test_model_without_app_languages_blocks_accept` |
| 6. The exact configured model ID is returned with task `text-to-speech` and languages `["en", "pt"]`, and the saved language is `pt` ⇒ `fetch_model_languages` raises `LanguageDiscoveryError`, Settings preserves `pt`, shows a retryable capability error, and permits saving an unrelated changed preference. | Tasks 1-2 | Task 1 Step 4 — invalid-task input; Task 2 Step 4 — `test_discovery_failure_preserves_language_and_allows_other_save` |
| 7. `GET /v1/models` returns the configured model record without a `language` field and the saved language is `pt` ⇒ the dialog preserves `pt`, disables the language control, shows the retryable capability error, and permits saving an unrelated changed preference. | Tasks 1-2 | Task 1 Step 4 — malformed-metadata input; Task 2 Step 4 — `test_discovery_failure_preserves_language_and_allows_other_save` |
| 8. `GET /v1/models` returns a valid response with no exact configured-model record and the saved language is `pt` ⇒ the dialog preserves `pt`, shows the model-unavailable retry state, and permits saving an unrelated changed preference. | Tasks 1-2 | Task 1 Step 4 — missing-model input; Task 2 Step 4 — `test_discovery_failure_preserves_language_and_allows_other_save` |
| 9. A mocked `/v1/models` request raises `requests.Timeout` ⇒ the GET call uses timeout `10`, the dialog preserves the saved language, shows Retry, and permits saving an unrelated changed preference. | Tasks 1-2 | Task 1 Step 4 — `test_transport_failures_raise_language_error`; Task 2 Step 4 — `test_discovery_failure_preserves_language_and_allows_other_save` |
| 10. `GET /v1/models` returns HTTP 401 and the saved language is `pt` ⇒ `fetch_model_languages` raises `LanguageDiscoveryError`, the dialog preserves `pt`, shows Retry, and permits saving an unrelated changed preference. | Tasks 1-2 | Task 1 Step 4 — `test_transport_failures_raise_language_error`; Task 2 Step 4 — `test_discovery_failure_preserves_language_and_allows_other_save` |
| 11. `GET /v1/models` returns HTTP 200 with invalid JSON and the saved language is `pt` ⇒ `fetch_model_languages` raises `LanguageDiscoveryError`, the dialog preserves `pt`, shows Retry, and permits saving an unrelated changed preference. | Tasks 1-2 | Task 1 Step 4 — `test_transport_failures_raise_language_error`; Task 2 Step 4 — `test_discovery_failure_preserves_language_and_allows_other_save` |
| 12. `GET /v1/models` returns the exact configured model with `language="en"` instead of a language-code list and the saved language is `pt` ⇒ `fetch_model_languages` raises `LanguageDiscoveryError`, the dialog preserves `pt`, and permits saving an unrelated changed preference. | Tasks 1-2 | Task 1 Step 4 — `test_missing_model_or_invalid_language_metadata_raises`; Task 2 Step 4 — `test_discovery_failure_preserves_language_and_allows_other_save` |
| 13. `fetch_model_languages("http://stt/", "Systran/faster-whisper-small", "k1")` ⇒ the only GET URL is `http://stt/v1/models`, no `/v1/registry` request is sent, and the header is `{"Authorization": "Bearer k1"}`. | Task 1 | Step 4 — `test_request_uses_models_path_bearer_and_empty_headers` |
| 14. `fetch_model_languages("http://stt", "Systran/faster-whisper-small", None)` ⇒ the request headers are `{}`. | Task 1 | Step 4 — `test_request_uses_models_path_bearer_and_empty_headers` |
| 15. A fresh config with no `transcription_language` value ⇒ `ConfigManager.get("transcription_language") == "en"`. | Task 1 | Step 4 — `test_transcription_language_and_model_defaults` |
| 16. A `settings.json` value `transcription_language="en"` with `WHISPER_TRANSCRIPTION_LANGUAGE="pt"` ⇒ the effective config value is `pt`. | Task 1 | Step 4 — `test_language_environment_override_and_saved_model_preservation` |
| 17. A fresh config with no `model_name` in `settings.json` ⇒ `ConfigManager.get("model_name") == "Systran/faster-whisper-small"`. | Task 1 | Step 4 — `test_transcription_language_and_model_defaults` |
| 18. A `settings.json` value `model_name="custom/model"` ⇒ the loaded config retains `custom/model` without migration. | Task 1 | Step 4 — `test_language_environment_override_and_saved_model_preservation` |
| 19. A successful dialog with the user selecting `pt` and accepting ⇒ `settings.json` contains `"transcription_language": "pt"`. | Tasks 2 and 4 | Task 2 Step 4 — `test_settings_acceptance_includes_selected_language`; Task 4 Step 4 — `test_settings_acceptance_persists_selected_language_to_file` |
| 20. `WhisperCodeApp` starts with `model_name="Systran/faster-whisper-small"` and `transcription_language="pt"`, then reloads config with `transcription_language="en"` ⇒ the transcriber uses the same effective model ID as discovery, has language `pt` at startup, and has language `en` after `_apply_settings`. | Task 4 | Step 4 — `test_transcription_language_initializes_and_hot_reloads` |
| 21. `APITranscriber` is constructed with model `Systran/faster-whisper-small` and language `pt`, then runs with audio bytes ⇒ `requests.post` receives multipart form data containing `language="pt"` and model `Systran/faster-whisper-small`. | Task 4 | Step 4 — `test_api_transcriber_run_posts_its_language` |
| 22. `APITranscriber` is constructed without a language argument ⇒ its language is `en`; calling the core `transcribe` function with audio bytes and no language argument ⇒ `requests.post` receives multipart form data containing `language="en"`. | Task 4 | Step 4 — `test_language_defaults_to_english_for_class_and_function` |
| 23. `check_grammar` receives Portuguese text `"Olá, mundo."` ⇒ the system prompt contains `"Preserve the input language. Do not translate."` and the user message content remains `"Olá, mundo."`. | Task 4 | Step 4 — `test_portuguese_refinement_prompt_preserves_language` |
| 24. A Portuguese transcription response `{"text":"Olá, mundo."}` with grammar checking disabled ⇒ the injector receives exactly `"Olá, mundo."` and no translation request is made. | Task 4 | Step 4 — `test_portuguese_transcript_is_injected_without_translation` |
| 25. K3 is configured with the currently pinned Speaches 0.7.0 CPU image, model ID `Systran/faster-whisper-small`, `DEFAULT_LANGUAGE=en`, CPU inference, `int8`, eight CPU threads, and a 4-GiB memory limit; after rollout the pod is Ready and the authenticated `/v1/models` response for that exact model has language metadata containing both `en` and `pt` (and, if present, task `automatic-speech-recognition`) ⇒ the K3 model-capability acceptance check passes. | Task 5 | Step 4 — Kustomize assertions and post-rollout `kubectl`/`curl` checks |
| 26. Settings opens while the mocked `GET /v1/models` response is pending ⇒ the Qt event loop continues processing a UI event and the dialog remains responsive. | Task 3 | Step 4 — `test_settings_event_loop_runs_while_get_is_blocked` |
| 27. The user changes STT URL, API key, and effective model ID in Settings, then activates Refresh ⇒ the worker requests `/v1/models` from the edited URL with the edited key and filters the edited model ID. | Task 3 | Step 4 — `test_refresh_uses_current_url_key_and_model` |
| 28. `/v1/models` returns HTTP 401 for a request using API key `secret-test-key` ⇒ the visible error text does not contain `secret-test-key`. | Task 3 | Step 4 — `test_http_401_with_api_key_is_not_exposed_in_error_text` |
| 29. The exact configured model advertises `language=["en", "pt"]` but omits `task`, matching Speaches 0.7.0 ⇒ `fetch_model_languages` returns exactly `["en", "pt"]`; a supplied non-ASR task remains rejected. | Task 1 | Step 4 — `test_accepts_exact_model_languages_when_speaches_omits_task_metadata` |

## Constraint Coverage

| Constraint | Verifying AC | Falsifier (what fails if the value changes) | Task | Verify step |
| --- | --- | --- | --- | --- |
| `APP_LANGUAGE_OPTIONS = (("en", "English"), ("pt", "Portuguese"))  # exposes only the two requested input languages, exercised by AC-1, AC-2, AC-4, and AC-5` | AC-1, AC-2 | The three-record fixture includes `en`, `pt`, and `es`; helper output and Settings item data must be exactly English/en and Portuguese/pt, with no Spanish or Auto-detect. | Tasks 1-2 | Step 4 — `test_filters_exact_asr_model_and_app_languages`; `test_language_combo_has_only_english_and_portuguese` |
| `DEFAULT_TRANSCRIPTION_LANGUAGE = "en"  # matches the current Speaches default, exercised by AC-15, AC-22, and AC-25` | AC-15, AC-22 | No saved language produces config `en`; omitted transcriber/function language produces multipart `en`. | Tasks 1, 4 | Step 4 — `test_transcription_language_and_model_defaults`; `test_language_defaults_to_english_for_class_and_function` |
| `LANGUAGE_CONFIG_KEY = "transcription_language"  # persisted setting name, exercised by AC-15, AC-16, and AC-19` | AC-15, AC-16, AC-19 | Tests read/write the literal `transcription_language` key; renaming it breaks the default, env override, or saved `pt` assertion. | Tasks 1, 2, and 4 | Step 4 — config tests; `test_settings_acceptance_includes_selected_language`; `test_settings_acceptance_persists_selected_language_to_file` |
| `LANGUAGE_ENV_VAR = "WHISPER_TRANSCRIPTION_LANGUAGE"  # environment override name, exercised by AC-16` | AC-16 | A file value `en` plus environment value `pt` must resolve to `pt`; a changed env name leaves `en`. | Task 1 | Step 4 — `test_language_environment_override_and_saved_model_preservation` |
| `SPEACHES_MODELS_PATH = "/v1/models"  # installed-model capability source, exercised by AC-1, AC-7 through AC-14, and AC-26 through AC-28` | AC-13 | The request built from base URL `http://stt/` must be exactly `http://stt/v1/models`; a changed path or registry call fails. | Task 1 | Step 4 — `test_request_uses_models_path_bearer_and_empty_headers` |
| `SPEACHES_MODELS_RESPONSE_SHAPE = {"data": [{"id": str, "task"?: str, "language": list[str]}]}  # model-list capability schema; task is optional in Speaches 0.7.0` | AC-1, AC-7, AC-12 | The exact three-record fixture yields `["en", "pt"]`; missing or string-valued `language` raises. | Tasks 1-2 | Step 4 — discovery filter and metadata-error tests |
| `SPEACHES_ASR_TASK = "automatic-speech-recognition"  # excludes non-ASR model records, exercised by AC-1 and AC-6` | AC-1, AC-6 | The configured ASR record is accepted while the same configured ID marked `text-to-speech` is rejected. | Tasks 1-2 | Step 4 — discovery filter and Settings error-state tests |
| Optional Speaches task metadata | AC-29 | An exact model with `language=["en", "pt"]` and no `task` returns both app languages, while an explicit non-ASR task remains rejected. | Task 1 | Step 4 — `test_accepts_exact_model_languages_when_speaches_omits_task_metadata` |
| `LANGUAGE_REQUEST_FIELD = "language"  # multipart field sent to STT, exercised by AC-21 and AC-22` | AC-21, AC-22 | The `pt` run and omitted-language run must send `data["language"]` equal to `pt` and `en`, respectively. | Task 4 | Step 4 — transcriber language request tests |
| `LANGUAGE_DISCOVERY_TIMEOUT_SECONDS = 10  # bounds a settings capability request, exercised by AC-9` | AC-9 | The timeout fake asserts the GET call's `timeout` argument is exactly `10`. | Task 1 | Step 4 — `test_transport_failures_raise_language_error` |
| `MULTILINGUAL_STT_MODEL_ID = "Systran/faster-whisper-small"  # shared app/K3 model ID, exercised by AC-17, AC-18, AC-20, AC-21, and AC-25` | AC-17, AC-20, AC-25 | Fresh config and K3 artifact must contain the exact ID, and app/transcriber must request that same ID; any mismatch fails. | Tasks 1, 4-5 | Step 4 — default config, CLI wire, Kustomize/live checks |
| `SPEACHES_IMAGE_VERSION = "0.7.0"  # retains the currently deployed API version, exercised by AC-25` | AC-25 | The rendered K3 deployment retains the pinned Speaches CPU image version `0.7.0`; changing the version breaks the real-manifest assertion. | Task 5 | Step 4 — Kustomize and post-rollout checks |
| `K3_DEFAULT_LANGUAGE = "en"  # preserves server default while requests send explicit language, exercised by AC-21, AC-22, and AC-25` | AC-25 | The real ConfigMap must retain `DEFAULT_LANGUAGE: en` while an explicit `pt` request remains covered by AC-21. | Tasks 4-5 | Step 4 — APITranscriber and Kustomize checks |
| `K3_INFERENCE_DEVICE = "cpu"  # retains CPU inference, exercised by AC-25` | AC-25 | Rendered configuration must contain `WHISPER__INFERENCE_DEVICE: cpu`. | Task 5 | Step 4 — Kustomize artifact assertions |
| `K3_COMPUTE_TYPE = "int8"  # retains CPU quantization, exercised by AC-25` | AC-25 | Rendered configuration must contain `WHISPER__COMPUTE_TYPE: int8`. | Task 5 | Step 4 — Kustomize artifact assertions |
| `K3_CPU_THREADS = 8  # retains current CPU thread setting, exercised by AC-25` | AC-25 | Rendered configuration must contain `WHISPER__CPU_THREADS: "8"`. | Task 5 | Step 4 — Kustomize artifact assertions |
| `K3_MEMORY_LIMIT_GIB = 4  # retains current pod memory ceiling, exercised by AC-25` | AC-25 | Rendered deployment must contain `memory: 4Gi`. | Task 5 | Step 4 — Kustomize artifact assertions |
| `GRAMMAR_LANGUAGE_PRESERVATION_INSTRUCTION = "Preserve the input language. Do not translate."  # keeps grammar refinement same-language, exercised by AC-23` | AC-23 | The exact prompt must be present for Portuguese input; removing or changing the instruction fails `test_portuguese_refinement_prompt_preserves_language`. | Task 4 | Step 4 — grammar prompt test |
