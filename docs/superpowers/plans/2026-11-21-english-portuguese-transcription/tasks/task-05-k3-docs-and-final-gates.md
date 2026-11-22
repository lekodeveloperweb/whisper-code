# Task 5

Update the K3 multilingual model, documentation, and final verification

**Files:**

- Modify in sibling repository: `/Users/lekodeveloperweb/workspace/ldw/projects/devops/ldw.solutions.vps.settings/K3/speaches/20-config.yaml`
- Modify in sibling repository: `/Users/lekodeveloperweb/workspace/ldw/projects/devops/ldw.solutions.vps.settings/K3/speaches/README.md`
- Modify: `docs/configuration.md`
- Modify: `docs/UI-WIREFRAMES.md`
- Modify: `docs/PRD.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`

**Interfaces:**

- Consumes: `MULTILINGUAL_STT_MODEL_ID`, `SPEACHES_IMAGE_VERSION`, `K3_DEFAULT_LANGUAGE`, `K3_INFERENCE_DEVICE`, `K3_COMPUTE_TYPE`, `K3_CPU_THREADS`, and `K3_MEMORY_LIMIT_GIB` from `../interfaces.md`, plus AC-25.
- Produces: multilingual K3 ConfigMap, updated preload/verification instructions, application documentation, and final suite/artifact evidence.

**Task-boundary preconditions for RED:** Tasks 1-4 are complete; the K3 repository is clean; its current Kustomize build renders eight Kubernetes documents and contains the old English-only model once.

**Required test-harness setup:** `kubectl` is available. Use the fixed sibling path below for local artifact checks. Live rollout/API verification requires the operator's Kubernetes context and `WHISPER_STT_API_URL` / `WHISPER_STT_API_KEY`; these were not available during plan preflight.

- [x] Step 1: Write the failing real-artifact gate

Run this shell gate before changing K3 or documentation; it must fail because the rendered ConfigMap still has the old model ID:

```bash
set -eu
K3_DIR=/Users/lekodeveloperweb/workspace/ldw/projects/devops/ldw.solutions.vps.settings/K3/speaches
rendered="$(kubectl kustomize "$K3_DIR")"
printf '%s\n' "$rendered" | rg -F 'Systran/faster-whisper-small'
```

- [x] Step 2: RED GATE

Run the exact shell block from Step 1. Expected RED: `rg` exits 1 because `kubectl kustomize` output contains `Systran/faster-distil-whisper-small.en` and not the multilingual ID. Paste the actual output and exit code.

- [x] Step 3: Implement

Change only the model ID in `20-config.yaml`; preserve the currently pinned Speaches 0.7.0 CPU image, `DEFAULT_LANGUAGE=en`, CPU inference, `int8`, eight CPU threads, and 4-GiB memory limit. Update the K3 README's pull/readiness/API verification commands. Update the five application documents with `transcription_language`, `WHISPER_TRANSCRIPTION_LANGUAGE`, the English/Portuguese choices, the model-ID migration note, and the no-translation behavior. Keep unrelated prose and deployment resources intact.

- [x] Step 4: GREEN and final gates

Run this real-artifact and documentation gate:

```bash
set -eu
K3_DIR=/Users/lekodeveloperweb/workspace/ldw/projects/devops/ldw.solutions.vps.settings/K3/speaches
rendered=/tmp/whisper-code-speaches-rendered.yaml
kubectl kustomize "$K3_DIR" > "$rendered"
test "$(rg -c '^apiVersion:' "$rendered")" -eq 8
test "$(rg -c 'Systran/faster-whisper-small' "$rendered")" -eq 1
rg -Fq 'ghcr.io/speaches-ai/speaches:0.7.0-cpu@sha256:09ccfe85e67267afb9f2eb483ff452ff0bb4f974bb7eae3b872026e6485e30ed' "$rendered"
! rg -Fq 'Systran/faster-distil-whisper-small.en' "$rendered"
rg -q '^  DEFAULT_LANGUAGE: en$' "$rendered"
rg -q '^  WHISPER__COMPUTE_TYPE: int8$' "$rendered"
rg -q '^  WHISPER__CPU_THREADS: "8"$' "$rendered"
rg -q '^  WHISPER__INFERENCE_DEVICE: cpu$' "$rendered"
rg -q 'memory: 4Gi' "$rendered"
docs=(docs/configuration.md docs/UI-WIREFRAMES.md docs/PRD.md AGENTS.md CLAUDE.md "$K3_DIR/README.md")
test "${#docs[@]}" -eq 6
for doc in "${docs[@]}"; do
    test -f "$doc"
done
for doc in docs/configuration.md docs/UI-WIREFRAMES.md docs/PRD.md AGENTS.md CLAUDE.md; do
    test -f "$doc"
    rg -q 'transcription_language' "$doc"
    rg -q 'WHISPER_TRANSCRIPTION_LANGUAGE' "$doc"
    rg -q 'Portuguese' "$doc"
    rg -q 'Systran/faster-whisper-small' "$doc"
    rg -q 'Existing settings.json model names are not migrated automatically' "$doc"
    rg -qi 'no translation|do not translate' "$doc"
done
rg -q 'Systran/faster-whisper-small' "$K3_DIR/README.md"
rg -q '/v1/models' "$K3_DIR/README.md"
```

Then run all final repository checks:

- `uv run pytest tests/ -v --cov=src/ --cov-report=term-missing`
- `uv run mypy src/`
- `uv run ruff check .`
- `uv run ruff format --check .` (the four pre-existing baseline failures must remain the only full-repository findings)
- `uv run ruff format --check src/core/api_language_discovery.py src/core/api_transcriber.py src/core/grammar_checker.py src/utils/config_manager.py src/gui/settings_dialog.py src/whisper_code/cli.py tests/test_api_language_discovery.py tests/test_config.py tests/test_settings_dialog.py tests/test_api_transcriber.py tests/test_cli.py tests/test_grammar_checker.py tests/test_integration.py`
- `uv run ruff format --check docs/superpowers/plans/2026-11-21-english-portuguese-transcription/interfaces.md docs/superpowers/plans/2026-11-21-english-portuguese-transcription/tasks/task-01-discovery-and-config.md docs/superpowers/plans/2026-11-21-english-portuguese-transcription/tasks/task-02-settings-language-ui.md docs/superpowers/plans/2026-11-21-english-portuguese-transcription/tasks/task-03-refresh-and-discovery-hardening.md docs/superpowers/plans/2026-11-21-english-portuguese-transcription/tasks/task-04-transcription-and-language-preservation.md docs/superpowers/plans/2026-11-21-english-portuguese-transcription/tasks/task-05-k3-docs-and-final-gates.md`
- `kubectl rollout status deployment/speaches -n speaches --timeout=10m`
- `curl -fsS -H "Authorization: Bearer ${WHISPER_STT_API_KEY:?set WHISPER_STT_API_KEY}" "${WHISPER_STT_API_URL:?set WHISPER_STT_API_URL}/v1/models" | python3 -c 'import json,sys; rows=json.load(sys.stdin)["data"]; found=[r for r in rows if r.get("id")=="Systran/faster-whisper-small" and r.get("task")=="automatic-speech-recognition"]; assert len(found)==1 and {"en","pt"}.issubset(set(found[0]["language"]))'

The deployment checks are run only after rollout and with operator-supplied credentials. The full formatter is expected to retain the four documented baseline Markdown-format failures; additionally run `uv run ruff format --check` on every changed Python source/test file and confirm no new formatter finding appears in plan Markdown.

- [x] Step 5: Record completion evidence

## Completion Evidence

- Baseline Kustomize render: 8 documents, old model once, new model absent; sibling repository was clean. `kubectl version --client` reported v1.37.2 / Kustomize v5.8.1.
- RED artifact gate: exact model `rg` returned exit code 1 with no output, as expected.
- Final Kustomize/docs gate: passed; `Kustomize docs=8 model_occurrences=1; documentation gate passed`. Image digest, CPU, `int8`, eight threads, 4-GiB memory, and `DEFAULT_LANGUAGE=en` assertions passed.
- `uv run pytest tests/ -q`: 295 passed in 5.36s. `uv run pytest tests/test_api_language_discovery.py -q`: 10 passed, including the regression for omitted `task` metadata. Full-suite coverage runs repeatedly segfaulted inside native PySide6/Qt timer processing (once in the Settings event-loop test and once in the tray-menu timer test); those coverage invocations did not complete or produce a valid coverage report. The full non-coverage suite passed, and the affected Settings test/file also passed in isolation.
- `uv run mypy src/`: no issues. `uv run ruff check .`: no issues. Changed Python files and the six plan Markdown files passed targeted `ruff format --check` (13 Python files and 6 plan files already formatted).
- `uv run ruff format --check .` still reports only the four pre-existing findings: `docs/PACKAGING.md`, `docs/api-reference.md`, `docs/superpowers/plans/2026-11-09-split-stt-llm-servers/interfaces.md`, and `docs/superpowers/plans/2026-11-09-split-stt-llm-servers/tasks/task-03-grammar-api-key.md`.
- Live K3 configuration applied in kubectl context `default` with `kubectl apply -k K3/speaches`; only `speaches-config` differed in the pre-apply diff. The ConfigMap and running pod both report `Systran/faster-whisper-small`, and the deployment rolled out successfully with 1/1 replicas ready. An authenticated in-pod `/v1/models` request found the exact model and verified advertised `en` and `pt`; Speaches 0.7.0 omits `task`. The discovery helper now accepts that exact-model/language shape while still rejecting an explicit non-ASR task. No API key was displayed. A subsequent final `kubectl get deployment` recheck could not reconnect to `127.0.0.1:16443` (connection refused), so the last observed ready state is the successful rollout result above.
- `git diff --check` passed. The sibling K3 repository is clean at `6d81edd` (`chore: update speaches service settings`); this session did not run a commit command.
