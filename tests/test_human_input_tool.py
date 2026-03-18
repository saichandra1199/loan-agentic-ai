"""Tests for tools/human_input_tool.py — TTY detection and fallbacks."""
from unittest.mock import patch
from tools.human_input_tool import ask_human


class TestAskHumanNonInteractive:
    def test_non_tty_returns_fallback_message(self):
        """In Docker/CI where stdin is not a terminal, returns graceful fallback."""
        with patch("sys.stdin.isatty", return_value=False):
            result = ask_human.func(question="What is the applicant's income?")
        assert "No interactive terminal" in result

    def test_non_tty_does_not_block(self):
        """Verify no input() call is attempted when not a TTY."""
        with patch("sys.stdin.isatty", return_value=False), \
             patch("builtins.input", side_effect=AssertionError("input() was called")):
            # Should NOT raise — input() must not be called
            result = ask_human.func(question="Any question")
        assert result  # returns something non-empty


class TestAskHumanInteractive:
    def test_tty_returns_user_input(self):
        with patch("sys.stdin.isatty", return_value=True), \
             patch("builtins.input", return_value="Monthly income is 150000"):
            result = ask_human.func(question="What is the income?")
        assert result == "Monthly income is 150000"

    def test_tty_empty_input_returns_no_answer(self):
        with patch("sys.stdin.isatty", return_value=True), \
             patch("builtins.input", return_value="  "):
            result = ask_human.func(question="Anything?")
        assert result == "No answer provided."

    def test_tty_eof_error_returns_fallback(self):
        """Handles unexpected stdin close gracefully."""
        with patch("sys.stdin.isatty", return_value=True), \
             patch("builtins.input", side_effect=EOFError):
            result = ask_human.func(question="What?")
        assert "No answer provided" in result
        assert isinstance(result, str)

    def test_tty_strips_whitespace(self):
        with patch("sys.stdin.isatty", return_value=True), \
             patch("builtins.input", return_value="  some answer  "):
            result = ask_human.func(question="Q?")
        assert result == "some answer"
