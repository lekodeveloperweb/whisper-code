"""Voice commands text processor for Whisper-Code.

Processes transcribed text through spoken-keyword transformations:
- "comma" -> ","
- "period" -> "."
- "new line" -> "\\n"
- "undo" -> backspace sentinel

Only replaces whole-word matches to avoid corrupting normal text
(e.g., "periodic" stays as "periodic", but "hello period" becomes "hello.").
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

logger: Any | None = None  # Avoid import on non-app startup


def _get_logger() -> Any:
    """Lazy-import logger to avoid PyQt dependency in tests."""
    global logger  # noqa: PLW0603
    if logger is None:
        from src.utils.logger import get_logger

        logger = get_logger()
    return logger


def _add_trailing_space_global(match: re.Match[str], default: str, processed: str) -> str:
    """Replace match, adding a space after the replacement if text follows."""
    if default == "\n":  # Newlines naturally separate text, no trailing space
        return default
    end = match.end()
    char_after: str = processed[end] if end < len(processed) else ""
    # Don't add trailing space when nothing follows (end of string)
    if char_after == "":
        return default
    if char_after not in (" ", "\n"):
        return default + " "
    return default


def _make_replacement(replacement: str, processed: str) -> Callable[[re.Match[str]], str]:
    """Create a regex replacement function with trailing-space handling.

    Args:
        replacement: The punctuation character to insert (e.g., ",", ".").
        processed: The current string being transformed (for boundary checks).

    Returns:
        A regex replacement function that inserts *replacement* with
        trailing-space handling based on what follows the match.
    """

    def replacer(m: re.Match[str]) -> str:
        return _add_trailing_space_global(m, replacement, processed)

    return replacer


def process_voice_commands(text: str, enabled: bool = True) -> str | tuple[str, str]:
    """Process voice commands in transcribed text.

    Replaces spoken keywords with their written equivalents:
    - "comma" -> ","
    - "period" -> "."
    - "new line" -> "\\n"
    - "undo" -> triggers backspace (sentinel returned)

    Only replaces whole-word matches to avoid corrupting normal text.
    For example, "periodic" stays as "periodic", but "hello period"
    becomes "hello.".

    Args:
        text: Raw transcribed text string.
        enabled: Whether voice commands are active.

    Returns:
        Processed text string. If "undo" is detected, returns a tuple
        (text, "undo") where text is the processed string and the second
        element signals the undo action.
    """
    if not enabled or not text:
        return text

    original = text.lower()

    # Check for "undo" command (standalone or at boundaries)
    # Matches "undo" as a whole word at start, end, or surrounded by spaces
    if re.search(r"\bundo\b", original):
        # Remove "undo" and any trailing words, return sentinel
        processed = re.sub(r"\bundo\b\s*", "", original).strip()
        _get_logger().info("Voice command: undo detected")
        return (processed, "undo")

    # Replace punctuation commands (case-insensitive, whole word)
    # Patterns consume leading AND trailing whitespace so the replacement
    # function can decide whether to add a space back.
    replacements: list[tuple[str, str]] = [
        (r"\s*new line\b\s*", "\n"),
        (r"\s*period\b *", "."),
        (r"\s*comma\b *", ","),
    ]

    def _add_trailing_space(match: re.Match[str], default: str) -> str:
        """Replace match, adding a space after the replacement if text follows."""
        return _add_trailing_space_global(match, default, processed)

    processed = str(text)  # explicit copy, not reference
    for pattern, replacement in replacements:
        processed = re.sub(
            pattern,
            _make_replacement(replacement, processed),  # pass replacement char
            processed,
            flags=re.IGNORECASE,
        )

    if processed != text:
        _get_logger().info(f"Voice commands applied: {repr(text)} -> {repr(processed)}")

    return processed
