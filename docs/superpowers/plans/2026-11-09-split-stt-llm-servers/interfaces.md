# Interfaces: Split STT and LLM Servers

Complete implementation code for every shared symbol. Tasks reference these
by name — never re-type a body in a task file.

## auth_headers (`src/utils/auth_headers.py`, new file)

```python
"""Shared Bearer-token header builder for OpenAI-compatible endpoints."""

from __future__ import annotations


def auth_headers(api_key: str | None) -> dict[str, str]:
    """Return request headers for an OpenAI-compatible endpoint.

    >>> auth_headers("sk-abc")
    {'Authorization': 'Bearer sk-abc'}
    >>> auth_headers(None)
    {}
    """
    if not api_key:
        return {}
    return {"Authorization": f"Bearer {api_key}"}
```

## ConfigManager changes (`src/utils/config_manager.py`)

Module constant, replacing the inline literal default (rename `api_url` →
`stt_api_url`, add three keys):

```python
STT_URL_DEFAULT = "http://localhost:8080"

DEFAULT_CONFIG: dict[str, str | int | bool | None] = {
    "stt_api_url": STT_URL_DEFAULT,
    "model_name": "whisper-large-v3",
    "model_quality": "accurate",
    "hotkey": "Cmd+Ctrl+T",
    "auto_insert": True,
    "sample_rate": 16000,
    "use_grammar_check": True,
    "grammar_model": "gemma4-e4b-8b",
    "silence_threshold_ms": 800,
    "voice_commands_enabled": True,
    "llm_api_url": None,
    "stt_api_key": None,
    "llm_api_key": None,
}

ENV_MAP: dict[str, tuple[str, type]] = {
    "stt_api_url": ("WHISPER_STT_API_URL", str),
    "model_name": ("WHISPER_MODEL_NAME", str),
    "model_quality": ("WHISPER_MODEL_QUALITY", str),
    "hotkey": ("WHISPER_HOTKEY", str),
    "auto_insert": ("WHISPER_AUTO_INSERT", bool),
    "sample_rate": ("WHISPER_SAMPLE_RATE", int),
    "use_grammar_check": ("WHISPER_GRAMMAR_CHECK", bool),
    "grammar_model": ("WHISPER_GRAMMAR_MODEL", str),
    "silence_threshold_ms": ("WHISPER_SILENCE_THRESHOLD", int),
    "voice_commands_enabled": ("WHISPER_VOICE_COMMANDS", bool),
    "llm_api_url": ("WHISPER_LLM_API_URL", str),
    "stt_api_key": ("WHISPER_STT_API_KEY", str),
    "llm_api_key": ("WHISPER_LLM_API_KEY", str),
}
```

New method on `ConfigManager`:

```python
    def resolved_llm_url(self) -> str:
        """Base URL for the chat/completions server.

        Returns llm_api_url when it is a non-empty string, else the STT
        stt_api_url, else STT_URL_DEFAULT.

        >>> ConfigManager().resolved_llm_url()  # both unset
        'http://localhost:8080'
        """
        llm = self.config.get("llm_api_url")
        if isinstance(llm, str) and llm != "":
            return llm
        stt = self.config.get("stt_api_url")
        if isinstance(stt, str) and stt != "":
            return stt
        return STT_URL_DEFAULT
```

## APITranscriber changes (`src/core/api_transcriber.py`)

Add import at the top of the file:

```python
from src.utils.auth_headers import auth_headers
```

Full replacement `__init__`:

```python
    def __init__(self, api_url: str, model_name: str, api_key: str | None = None) -> None:
        """Initialize the transcriber with API URL, model, and optional key.

        Args:
            api_url: Base URL of the STT API (e.g. http://localhost:8080).
            model_name: Model identifier for transcription.
            api_key: Bearer token for the STT server; None/empty sends
                no Authorization header.
        """
        super().__init__()
        self.base_url: str = api_url.rstrip("/")
        self.api_endpoint: str = f"{self.base_url}/v1/audio/transcriptions"
        self.model_name: str = model_name
        self.api_key: str | None = api_key
        self.audio_data: bytes | None = None
        self.last_result: str = ""
```

Full replacement `run` (delegates to `transcribe`, mirroring
`GrammarChecker.run` — removes the duplicated POST body):

```python
    def run(self) -> None:
        """Execute the transcription request in a background thread.

        Delegates to the transcribe function, wiring up the Qt signal
        emitters as callbacks, and records the result for the grammar
        checker fallback path.
        """
        result = transcribe(
            api_endpoint=self.api_endpoint,
            model_name=self.model_name,
            audio_data=self.audio_data,
            finished_cb=self.finished.emit,
            error_cb=self.error.emit,
            confidence_cb=self.confidence_changed.emit,
            api_key=self.api_key,
        )
        if result is not None:
            self.last_result = result
```

Full replacement `transcribe` (gains `api_key`; `_handle_error` and
`_process_success` stay unchanged):

```python
def transcribe(
    api_endpoint: str,
    model_name: str,
    audio_data: bytes | None,
    finished_cb: TranscribeFinishedCb | None = None,
    error_cb: TranscribeErrorCb | None = None,
    confidence_cb: TranscribeConfidenceCb | None = None,
    api_key: str | None = None,
) -> str | None:
    """Core transcription logic. Extracted for testability.

    Accepts callback functions instead of Qt signals so it can be
    tested without a running Qt event loop.

    Args:
        api_endpoint: Full endpoint URL for the STT API.
        model_name: Model identifier for transcription.
        audio_data: WAV audio bytes to transcribe.
        finished_cb: Callback invoked with the transcribed text.
        error_cb: Callback invoked on errors.
        confidence_cb: Callback invoked with the confidence score.
        api_key: Bearer token; None/empty sends no Authorization header.

    Returns:
        The transcribed text on success, None on failure.
    """
    if not audio_data:
        _handle_error(error_cb, "No audio data provided")
        return None

    try:
        files: dict[str, tuple[str, bytes, str]] = {
            "file": ("audio.wav", audio_data, "audio/wav")
        }
        payload: dict[str, str] = {"model": model_name}

        response = requests.post(
            api_endpoint,
            files=files,
            data=payload,
            headers=auth_headers(api_key),
            timeout=120,
        )

        if response.status_code == HTTP_OK:
            return _process_success(response, finished_cb, confidence_cb)
        if error_cb:
            error_cb(f"API Error (Status {response.status_code}): {response.text}")
        return None

    except RequestsException as e:
        error_msg = f"Connection error: {str(e)}"
        _handle_error(error_cb, error_msg)
        return None
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        _handle_error(error_cb, error_msg)
        return None
```

## GrammarChecker changes (`src/core/grammar_checker.py`)

Add import at the top of the file:

```python
from src.utils.auth_headers import auth_headers
```

Full replacement `check_grammar` (gains `api_key`; system prompt and payload
dict stay byte-for-byte identical):

```python
def check_grammar(
    api_endpoint: str,
    model_name: str,
    text: str,
    finished_cb: CheckGrammarFinishedCb | None = None,
    error_cb: CheckGrammarErrorCb | None = None,
    api_key: str | None = None,
) -> str | None:
    """Core grammar checking logic. Extracted for testability.

    Sends the text to an OpenAI-compatible chat API for grammatical
    refinement. The system prompt instructs the model to correct
    capitalization, punctuation, syntax, and disfluencies.

    Args:
        api_endpoint: Full endpoint URL for the chat completions API.
        model_name: Model identifier for grammar refinement.
        text: The text to correct.
        finished_cb: Callback invoked with the corrected text.
        error_cb: Callback invoked on errors.
        api_key: Bearer token; None/empty sends no Authorization header.

    Returns:
        The corrected text on success, None on failure.
    """
    if not text:
        if error_cb:
            error_cb("No text provided")
        return None

    system_prompt: str = (
        "You are a specialized technical editor. Analyze the following transcription "
        "for grammatical precision. Correct all capitalization, punctuation, and "
        "syntactical errors. Eliminate verbal disfluencies and repetitions. Keep the "
        "output clinical and concise. "
        "Output ONLY the corrected string for the user input, anything else."
    )

    payload: dict[str, Any] = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        "stream": False,
        "temperature": 0.6,
        "max_tokens": 4096,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0,
        "repetition_penalty": 1,
        "presence_penalty": 0,
        "chat_template_kwargs": {"enable_thinking": False},
    }

    try:
        response = requests.post(
            api_endpoint,
            json=payload,
            headers=auth_headers(api_key),
            timeout=30,
        )
        if response.status_code == HTTP_OK:
            response_json = response.json()
            corrected: str = response_json["choices"][0]["message"]["content"].strip()
            if corrected.startswith('"') and corrected.endswith('"'):
                corrected = corrected[1:-1]
            if finished_cb:
                finished_cb(corrected)
            return corrected
        if error_cb:
            error_cb(f"SLM API Error: {response.status_code}")
        return None
    except Exception as e:
        if error_cb:
            error_cb(str(e))
        return None
```

Full replacement `GrammarChecker.__init__` and `run`:

```python
    def __init__(self, api_url: str, model_name: str, api_key: str | None = None) -> None:
        """Initialize the grammar checker with API URL, model, optional key.

        Args:
            api_url: Base URL of the chat completions API.
            model_name: Model identifier for grammar refinement.
            api_key: Bearer token for the LLM server; None/empty sends
                no Authorization header.
        """
        super().__init__()
        self.api_endpoint: str = f"{api_url.rstrip('/')}/v1/chat/completions"
        self.model_name: str = model_name
        self.api_key: str | None = api_key
        self.text_to_fix: str = ""
```

```python
    def run(self) -> None:
        """Execute the grammar check in a background thread.

        Delegates to the check_grammar function, wiring up the
        Qt signal emitters as callbacks.
        """
        check_grammar(
            api_endpoint=self.api_endpoint,
            model_name=self.model_name,
            text=self.text_to_fix,
            finished_cb=self.finished.emit,
            error_cb=self.error.emit,
            api_key=self.api_key,
        )
```

## WhisperCodeApp changes (`src/whisper_code/cli.py`)

Update the config import:

```python
from src.utils.config_manager import STT_URL_DEFAULT, ConfigManager
```

New helper method:

```python
    def _optional_str(self, key: str) -> str | None:
        """Read a string config key, treating None and empty as unset."""
        value = self.config.get(key)
        return str(value) if value else None
```

Full replacement `_make_transcriber`:

```python
    def _make_transcriber(self) -> APITranscriber:
        """Create APITranscriber configured with quality-resolved model name."""
        from src.utils.model_quality import resolve_model_name

        stt_url: str = str(self.config.get("stt_api_url") or STT_URL_DEFAULT)
        stt_key: str | None = self._optional_str("stt_api_key")
        model_quality: str = str(self.config.get("model_quality") or "accurate")
        custom_model_name: str | None = self.config.get("model_name")  # type: ignore[assignment]

        resolved_model: str = resolve_model_name(model_quality, custom_model_name)
        return APITranscriber(stt_url, resolved_model, stt_key)
```

Full replacement `_make_grammar_checker`:

```python
    def _make_grammar_checker(self) -> GrammarChecker:
        """Create GrammarChecker configured from settings.

        The endpoint comes from resolved_llm_url so an unset llm_api_url
        reuses the STT server; llm_api_key is read only for this server.
        """
        grammar_model: str = str(self.config.get("grammar_model") or "gemma4-e4b-8b")
        return GrammarChecker(
            self.config.resolved_llm_url(),
            grammar_model,
            self._optional_str("llm_api_key"),
        )
```

Full replacement `_log_startup` (logs both URLs, never keys):

```python
    def _log_startup(self) -> None:
        """Emit startup log with both server URLs, models, and hotkey.

        API keys are never interpolated into any log line.
        """
        from src.utils.model_quality import resolve_model_name

        logger.info("\n" + "=" * 50)
        logger.info("Whisper-Code is running!")
        logger.info(f"STT API URL: {self.config.get('stt_api_url')}")
        model_quality: str = str(self.config.get("model_quality") or "accurate")
        custom_model: str | None = self.config.get("model_name")  # type: ignore[assignment]
        resolved: str = resolve_model_name(model_quality, custom_model)
        logger.info(f"STT Model:   {resolved} (quality: {model_quality})")
        logger.info(f"LLM API URL: {self.config.resolved_llm_url()}")
        if self.config.get("use_grammar_check"):
            logger.info(f"SLM Model:   {self.config.get('grammar_model')}")
        logger.info("Hotkey:  Cmd + Ctrl + T")
        logger.info("=" * 50 + "\n")
```

In `_apply_settings`, the line `self._apply_api_url()` becomes
`self._apply_stt_url()`.

Full replacement of `_apply_api_url` (renamed to `_apply_stt_url`):

```python
    def _apply_stt_url(self) -> None:
        """Update STT API URL and key if changed."""
        new_url = str(self.config.get("stt_api_url") or STT_URL_DEFAULT)
        if new_url != self.transcriber.base_url:
            logger.debug(f"STT API URL changed to: {new_url}")
            self.transcriber.base_url = new_url
            self.transcriber.api_endpoint = f"{new_url.rstrip('/')}/v1/audio/transcriptions"
        new_key = self._optional_str("stt_api_key")
        if new_key != self.transcriber.api_key:
            logger.debug("STT API key changed")
            self.transcriber.api_key = new_key
```

Full replacement `_apply_grammar_config` (endpoint from the fallback rule;
model-name lines are kept from the existing body, verbatim):

```python
    def _apply_grammar_config(self) -> None:
        """Update grammar checker endpoint, model, and key if changed."""
        new_endpoint = f"{self.config.resolved_llm_url().rstrip('/')}/v1/chat/completions"
        if new_endpoint != self.grammar_checker.api_endpoint:
            logger.debug(f"Grammar API URL changed to: {new_endpoint}")
            self.grammar_checker.api_endpoint = new_endpoint
        new_grammar_model = str(self.config.get("grammar_model") or "gemma4-e4b-8b")
        if new_grammar_model != self.grammar_checker.model_name:
            logger.debug(f"Grammar model changed to: {new_grammar_model}")
            self.grammar_checker.model_name = new_grammar_model
        new_key = self._optional_str("llm_api_key")
        if new_key != self.grammar_checker.api_key:
            logger.debug("Grammar API key changed")
            self.grammar_checker.api_key = new_key
```

## SettingsDialog changes (`src/gui/settings_dialog.py`)

New widget creation lines in `__init__`, immediately after the existing
`self._api_edit: QLineEdit = QLineEdit()` line:

```python
        self._stt_key_edit: QLineEdit = QLineEdit()
        self._stt_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._llm_api_edit: QLineEdit = QLineEdit()
        self._llm_key_edit: QLineEdit = QLineEdit()
        self._llm_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
```

In `__init__`, extend `_widget_refs` with the four new widgets, immediately
after `self._api_edit,`:

```python
            self._stt_key_edit,
            self._llm_api_edit,
            self._llm_key_edit,
```

Full replacement `_setup_ui`:

```python
    def _setup_ui(self) -> None:
        """Build the settings dialog using Qt layouts for proper formatting."""
        main_layout = QVBoxLayout(self)

        # --- STT Server group ---
        stt_group: QGroupBox = QGroupBox("STT Server")
        stt_form = QFormLayout(stt_group)

        self._api_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        stt_form.addRow("API &URL:", self._api_edit)

        self._stt_key_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        stt_form.addRow("API K&ey:", self._stt_key_edit)

        self._model_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        stt_form.addRow("&Model Name:", self._model_edit)

        self._quality_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        stt_form.addRow("Model &Quality:", self._quality_combo)

        main_layout.addWidget(stt_group)

        # --- LLM Server group ---
        llm_group: QGroupBox = QGroupBox("LLM Server")
        llm_form = QFormLayout(llm_group)

        self._llm_api_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        llm_form.addRow("LLM &URL:", self._llm_api_edit)

        self._llm_key_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        llm_form.addRow("LLM Ke&y:", self._llm_key_edit)

        self._grammar_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        llm_form.addRow("&Grammar Model:", self._grammar_edit)

        self._grammar_check.setText("Enable grammar checking")
        llm_form.addRow(self._grammar_check)

        main_layout.addWidget(llm_group)

        # --- Hotkey group ---
        hotkey_group: QGroupBox = QGroupBox("Hotkey")
        hotkey_layout = QHBoxLayout(hotkey_group)

        self._hotkey_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._recording_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self._recording_label.setVisible(False)

        hotkey_layout.addWidget(QLabel("Custom Hotkey:"))
        hotkey_layout.addWidget(self._hotkey_edit)
        hotkey_layout.addWidget(self._recording_label, stretch=1)
        hotkey_layout.addWidget(self._record_button)

        main_layout.addWidget(hotkey_group)

        # --- Preferences group ---
        prefs_group: QGroupBox = QGroupBox("Preferences")
        prefs_form = QFormLayout(prefs_group)

        self._auto_insert_check.setText("Auto-insert after transcription")
        prefs_form.addRow(self._auto_insert_check)

        self._sample_spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        prefs_form.addRow("&Sample Rate (Hz):", self._sample_spin)

        self._silence_spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        prefs_form.addRow("&Silence Threshold (ms):", self._silence_spin)

        self._voice_commands_check.setText("Enable voice commands")
        prefs_form.addRow(self._voice_commands_check)

        main_layout.addWidget(prefs_group)

        # Spacer pushes OK/Cancel to bottom
        main_layout.addStretch()

        # OK/Cancel buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        main_layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Store reference to prevent GC
        self._widget_refs.append(button_box)
```

Full replacement `_populate_widgets`:

```python
    def _populate_widgets(self) -> None:
        self._api_edit.setText(str(self._config.get("stt_api_url") or ""))
        self._stt_key_edit.setText(str(self._config.get("stt_api_key") or ""))
        self._llm_api_edit.setText(str(self._config.get("llm_api_url") or ""))
        self._llm_key_edit.setText(str(self._config.get("llm_api_key") or ""))
        self._model_edit.setText(str(self._config.get("model_name") or ""))
        self._hotkey_edit.setText(str(self._config.get("hotkey") or ""))
        self._auto_insert_check.setChecked(bool(self._config.get("auto_insert")))
        self._sample_spin.setValue(int(self._config.get("sample_rate") or 16000))
        self._silence_spin.setValue(int(self._config.get("silence_threshold_ms") or 800))
        self._grammar_check.setChecked(bool(self._config.get("use_grammar_check")))
        self._grammar_edit.setText(str(self._config.get("grammar_model") or ""))
        quality: str = str(self._config.get("model_quality") or "accurate")
        if quality in ("fast", "balanced", "accurate"):
            idx: int = ["fast", "balanced", "accurate"].index(quality)
            self._quality_combo.setCurrentIndex(idx)
        self._voice_commands_check.setChecked(bool(self._config.get("voice_commands_enabled")))
```

Full replacement `_apply_config`:

```python
    def _apply_config(self) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        updates["stt_api_url"] = self._api_edit.text()
        updates["stt_api_key"] = self._stt_key_edit.text()
        updates["llm_api_url"] = self._llm_api_edit.text()
        updates["llm_api_key"] = self._llm_key_edit.text()
        updates["model_name"] = self._model_edit.text()
        updates["hotkey"] = self._hotkey_edit.text()
        updates["auto_insert"] = self._auto_insert_check.isChecked()
        updates["sample_rate"] = self._sample_spin.value()
        updates["silence_threshold_ms"] = self._silence_spin.value()
        updates["use_grammar_check"] = self._grammar_check.isChecked()
        updates["grammar_model"] = self._grammar_edit.text()
        updates["model_quality"] = self._quality_combo.currentText()
        updates["voice_commands_enabled"] = self._voice_commands_check.isChecked()
        return updates
```
