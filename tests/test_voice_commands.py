"""Tests for voice_commands module."""

from __future__ import annotations

from src.utils.voice_commands import process_voice_commands


class TestProcessVoiceCommands:
    """Test voice command text transformation."""

    def test_no_commands_returns_text_unchanged(self):
        assert process_voice_commands("hello world") == "hello world"

    def test_comma_command_replaced(self):
        result = process_voice_commands("hello comma world")
        assert result == "hello, world"

    def test_period_command_replaced(self):
        result = process_voice_commands("hello period")
        assert result == "hello."

    def test_new_line_command_replaced(self):
        result = process_voice_commands("first line new line second line")
        assert result == "first line\nsecond line"

    def test_multiple_commands(self):
        result = process_voice_commands("hello comma world period new line again")
        assert result == "hello, world.\nagain"

    def test_case_insensitive_comma(self):
        result = process_voice_commands("hello COMMA world")
        assert result == "hello, world"

    def test_case_insensitive_period(self):
        result = process_voice_commands("hello PERIOD")
        assert result == "hello."

    def test_case_insensitive_new_line(self):
        result = process_voice_commands("first NEW LINE second")
        assert result == "first\nsecond"

    def test_subword_not_replaced(self):
        """Words containing command words should NOT be replaced."""
        result = process_voice_commands("periodic table comma")
        assert result == "periodic table,"

    def test_subword_new_line_not_replaced(self):
        """'newline' (one word) should NOT trigger — 'new line' (two words) does."""
        result = process_voice_commands("newline is one word")
        assert result == "newline is one word"

    def test_undo_command_returns_tuple(self):
        result = process_voice_commands("hello undo world")
        assert isinstance(result, tuple)
        assert result[1] == "undo"
        assert "undo" not in result[0].lower()

    def test_undo_at_start(self):
        result = process_voice_commands("undo everything")
        assert isinstance(result, tuple)
        assert result[1] == "undo"

    def test_undo_standalone(self):
        result = process_voice_commands("undo")
        assert isinstance(result, tuple)
        assert result[1] == "undo"

    def test_disabled_does_nothing(self):
        result = process_voice_commands("hello comma world", enabled=False)
        assert result == "hello comma world"

    def test_empty_text_returns_unchanged(self):
        assert process_voice_commands("") == ""

    def test_none_text_returns_none(self):
        assert process_voice_commands(None) is None

    def test_complex_sentence(self):
        text = "greet the boss comma say hello period new line goodbye period"
        result = process_voice_commands(text)
        assert result == "greet the boss, say hello.\ngoodbye."

    def test_period_at_end_of_sentence(self):
        result = process_voice_commands("that is great period")
        assert result == "that is great."
