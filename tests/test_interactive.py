"""
Scenarios: interactive session commands, LLM query, history tracking,
           conversation context building, error handling.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nexarq_cli.agents.base import AgentResult, Severity
from nexarq_cli.cli.interactive import InteractiveSession
from nexarq_cli.llm.base import LLMResponse


def _result(name, severity=Severity.HIGH, output="Found issues."):
    return AgentResult(agent_name=name, severity=severity, output=output, latency_ms=100)


def _make_session(results=None):
    if results is None:
        results = [
            _result("security", Severity.CRITICAL, "SQL injection in auth.py line 42"),
            _result("review", Severity.MEDIUM, "Missing docstrings in 3 functions"),
            _result("performance", Severity.HIGH, "N+1 query in user_list endpoint"),
        ]
    provider = MagicMock()
    provider.complete.return_value = LLMResponse(
        text="Here is my analysis of the findings.",
        provider="mock", model="mock",
        prompt_tokens=50, completion_tokens=100,
    )
    diff = "diff --git a/auth.py b/auth.py\n+password = 'hardcoded'"
    return InteractiveSession(results=results, diff=diff, provider=provider), provider


class TestInteractiveSessionBuild:
    def test_system_prompt_contains_results(self):
        session, _ = _make_session()
        assert "SQL injection" in session._system
        assert "SECURITY" in session._system

    def test_system_prompt_contains_diff(self):
        session, _ = _make_session()
        assert "auth.py" in session._system

    def test_system_prompt_truncates_large_diff(self):
        large_diff = "+" + "x" * 10_000
        results = [_result("review")]
        provider = MagicMock()
        session = InteractiveSession(results=results, diff=large_diff, provider=provider)
        assert "truncated" in session._system

    def test_format_results_includes_all_agents(self):
        session, _ = _make_session()
        formatted = session._format_results()
        assert "SECURITY" in formatted
        assert "REVIEW" in formatted
        assert "PERFORMANCE" in formatted

    def test_format_results_handles_error_result(self):
        results = [AgentResult(agent_name="bugs", severity=Severity.HIGH,
                               output="", error="Timeout after 120s")]
        session = InteractiveSession(results=results, diff="", provider=MagicMock())
        formatted = session._format_results()
        assert "ERROR" in formatted
        assert "Timeout" in formatted


class TestInteractiveSessionQuery:
    def test_ask_calls_provider(self):
        session, provider = _make_session()
        session._ask("What is the most critical issue?")
        provider.complete.assert_called_once()

    def test_ask_adds_to_history(self):
        session, provider = _make_session()
        session._ask("Explain the SQL injection")
        assert len(session._history) == 1
        assert session._history[0]["user"] == "Explain the SQL injection"
        assert session._history[0]["assistant"] != ""

    def test_ask_includes_history_in_next_prompt(self):
        session, provider = _make_session()
        session._ask("First question")
        session._ask("Follow-up question")
        # Second call prompt should include first turn
        second_call_prompt = provider.complete.call_args_list[1][0][0]
        assert "First question" in second_call_prompt

    def test_ask_handles_provider_error(self):
        session, provider = _make_session()
        provider.complete.side_effect = RuntimeError("Network error")
        session._ask("Will this crash?")   # should not raise
        assert len(session._history) == 0  # error means nothing added

    def test_history_limited_to_last_6_turns(self):
        session, provider = _make_session()
        for i in range(10):
            session._history.append({"user": f"q{i}", "assistant": f"a{i}"})

        session._ask("Final question")
        prompt = provider.complete.call_args[0][0]
        # Only last 6 turns in context
        assert "q3" in prompt or "q4" in prompt  # recent ones present
        assert "q0" not in prompt  # oldest ones dropped


class TestInteractiveSessionCommands:
    def _run_command(self, session, command):
        """Simulate a single command without entering the full loop."""
        with patch("nexarq_cli.cli.interactive.Prompt.ask", side_effect=[command, "/exit"]):
            session.start()

    def test_exit_command_stops_loop(self):
        session, _ = _make_session()
        with patch("nexarq_cli.cli.interactive.Prompt.ask", return_value="/exit"):
            session.start()   # should return cleanly

    def test_quit_command_stops_loop(self):
        session, _ = _make_session()
        with patch("nexarq_cli.cli.interactive.Prompt.ask", return_value="quit"):
            session.start()

    def test_agents_command_no_crash(self):
        session, provider = _make_session()
        with patch("nexarq_cli.cli.interactive.Prompt.ask", side_effect=["/agents", "/exit"]):
            session.start()
        provider.complete.assert_not_called()  # /agents is built-in, no LLM call

    def test_findings_command_no_crash(self):
        session, provider = _make_session()
        with patch("nexarq_cli.cli.interactive.Prompt.ask", side_effect=["/findings", "/exit"]):
            session.start()
        provider.complete.assert_not_called()

    def test_empty_input_ignored(self):
        session, provider = _make_session()
        with patch("nexarq_cli.cli.interactive.Prompt.ask", side_effect=["", "  ", "/exit"]):
            session.start()
        provider.complete.assert_not_called()

    def test_real_question_calls_llm(self):
        session, provider = _make_session()
        with patch("nexarq_cli.cli.interactive.Prompt.ask",
                   side_effect=["How do I fix the SQL injection?", "/exit"]):
            session.start()
        provider.complete.assert_called_once()

    def test_keyboard_interrupt_exits_cleanly(self):
        session, _ = _make_session()
        with patch("nexarq_cli.cli.interactive.Prompt.ask", side_effect=KeyboardInterrupt):
            session.start()   # should not propagate the exception
