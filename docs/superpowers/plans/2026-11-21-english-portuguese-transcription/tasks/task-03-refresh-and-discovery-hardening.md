# Task 3

Complete Settings refresh, responsiveness, and secret-safe error handling

**Files:**

- Modify: `src/gui/settings_dialog.py`
- Modify/Test: `tests/test_settings_dialog.py`

**Interfaces:**

- Consumes: `make_dialog`, `FakeConfig`, and Settings state handlers from Task 2; `_LanguageDiscoveryWorker` from `../interfaces.md`.
- Produces: Refresh/Retry button wiring that uses current settings inputs, responsive async discovery, secret-safe status text.

**Task-boundary preconditions for RED:** Task 2 is complete; opening Settings starts the worker and applies capability/error states; worker is retained on the dialog.

**Required test-harness setup:** Reuse the `qapp`, `make_dialog`, and `FakeConfig` setup added in Task 2. Use a blocking `requests.get` fake controlled by `threading.Event`; release it in `finally` so a failed assertion cannot leave a running QThread.

- [x] Step 1: Write the failing tests

Add to `tests/test_settings_dialog.py`:

```python
from threading import Event
from unittest.mock import MagicMock, patch

import requests
from PySide6.QtCore import QTimer

from src.gui.settings_dialog import SettingsDialog, _LanguageDiscoveryWorker


def test_refresh_uses_current_url_key_and_model(qapp):
    dialog = make_dialog(qapp)
    dialog._api_edit.setText("http://changed-stt/")
    dialog._stt_key_edit.setText("changed-key")
    dialog._model_edit.setText("Systran/faster-whisper-small")
    worker = MagicMock()
    with patch("src.gui.settings_dialog._LanguageDiscoveryWorker", return_value=worker) as factory:
        dialog._refresh_button.click()
        assert not dialog._refresh_button.isEnabled()
        dialog._start_language_discovery()
    factory.assert_called_once_with(
        "http://changed-stt/",
        "Systran/faster-whisper-small",
        "changed-key",
    )
    worker.start.assert_called_once_with()


def test_http_401_with_api_key_is_not_exposed_in_error_text(qapp):
    response = MagicMock()
    response.raise_for_status.side_effect = requests.HTTPError("401")
    errors = []
    worker = _LanguageDiscoveryWorker("http://stt", "model", "secret-test-key")
    worker.failed.connect(errors.append)
    with patch("src.core.api_language_discovery.requests.get", return_value=response) as get:
        worker.run()
    assert get.call_args.kwargs["headers"] == {"Authorization": "Bearer secret-test-key"}
    dialog = make_dialog(qapp)
    dialog._on_language_discovery_failed(errors[0])
    assert "secret-test-key" not in dialog._language_status.text()


def test_settings_event_loop_runs_while_get_is_blocked(qapp):
    started = Event()
    release = Event()
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"data": []}

    def blocked_get(*args, **kwargs):
        started.set()
        release.wait(2)
        return response

    dialog = None
    try:
        with patch("src.core.api_language_discovery.requests.get", side_effect=blocked_get):
            dialog = SettingsDialog(FakeConfig(transcription_language="en"))
            assert started.wait(1)
            processed = []
            QTimer.singleShot(0, lambda: processed.append(True))
            qapp.processEvents()
            assert processed == [True]
    finally:
        release.set()
        if dialog is not None:
            worker = dialog._language_worker
            if worker is not None:
                worker.wait(1000)
            qapp.processEvents()
            dialog.close()
```

- [x] Step 2: RED GATE

Run: `uv run pytest tests/test_settings_dialog.py -q`

Expected RED: the refresh-button test fails because the control is absent or does not use the edited URL/key/model; the responsiveness test must not fail from a fixture or import error. Paste the actual output.

- [x] Step 3: Implement

Add the Refresh/Retry control and connect it to `_start_language_discovery()`. Build each worker from the current STT URL, API key, and effective model ID. Keep only the active worker referenced, disable duplicate refresh while it runs, and ensure completion handlers update the dialog on the Qt thread. Error text must use the sanitized discovery message and never include the key or raw response body.

- [x] Step 4: GREEN

Run: `uv run pytest tests/test_settings_dialog.py -q`

Expected output: all Settings tests pass. These tests catch stale-field discovery, a UI-thread network stall, a leaked API key, and a worker that outlives its dialog.

- [x] Step 5: Record completion evidence

Record the exact command and actual output. Do not commit.
