from __future__ import annotations

from collections.abc import Callable
from typing import Any

import requests
from PySide6.QtCore import QThread
from PySide6.QtCore import Signal as pyqtSignal

HTTP_OK = 200

CheckGrammarFinishedCb = Callable[[str], None]
CheckGrammarErrorCb = Callable[[str], None]


def check_grammar(
    api_endpoint: str,
    model_name: str,
    text: str,
    finished_cb: CheckGrammarFinishedCb | None = None,
    error_cb: CheckGrammarErrorCb | None = None,
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
        response = requests.post(api_endpoint, json=payload, timeout=30)
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


class GrammarChecker(QThread):
    """Check grammar of transcribed text in a background thread.

    Wraps the check_grammar function as a QThread for use within
    the Qt event loop. Emits signals on completion or error.
    """

    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_url: str, model_name: str) -> None:
        """Initialize the grammar checker with API URL and model name.

        Args:
            api_url: Base URL of the chat completions API.
            model_name: Model identifier for grammar refinement.
        """
        super().__init__()
        self.api_endpoint: str = f"{api_url.rstrip('/')}/v1/chat/completions"
        self.model_name: str = model_name
        self.text_to_fix: str = ""

    def set_text(self, text: str) -> None:
        """Set the text to be grammar-checked.

        Args:
            text: The text to correct.
        """
        self.text_to_fix = text

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
        )
