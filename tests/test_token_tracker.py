"""Tests for TokenTracker – SRS 3.11 token governance."""
from __future__ import annotations

import pytest

from nexarq_cli.agents.base import AgentResult, Severity
from nexarq_cli.reporting.token_tracker import TokenTracker, TokenUsageSummary


def _result(agent: str, prompt: int = 100, completion: int = 200) -> AgentResult:
    return AgentResult(
        agent_name=agent,
        severity=Severity.MEDIUM,
        output="test output",
        token_usage={"prompt": prompt, "completion": completion},
    )


class TestTokenTrackerBasics:
    def test_initial_totals_are_zero(self):
        t = TokenTracker()
        s = t.summary()
        assert s.total_tokens == 0
        assert s.total_prompt == 0
        assert s.total_completion == 0

    def test_record_accumulates_tokens(self):
        t = TokenTracker()
        t.record(_result("security", 100, 200))
        s = t.summary()
        assert s.total_prompt == 100
        assert s.total_completion == 200
        assert s.total_tokens == 300

    def test_multiple_records_accumulated(self):
        t = TokenTracker()
        t.record(_result("security", 100, 200))
        t.record(_result("bugs", 50, 150))
        s = t.summary()
        assert s.total_prompt == 150
        assert s.total_completion == 350
        assert s.total_tokens == 500

    def test_by_agent_breakdown(self):
        t = TokenTracker()
        t.record(_result("security", 100, 200))
        t.record(_result("bugs", 50, 75))
        s = t.summary()
        assert "security" in s.by_agent
        assert s.by_agent["security"]["prompt"] == 100
        assert s.by_agent["bugs"]["completion"] == 75

    def test_zero_tokens_result_recorded(self):
        t = TokenTracker()
        r = AgentResult(agent_name="explain", severity=Severity.INFO, output="ok")
        t.record(r)
        s = t.summary()
        assert s.total_tokens == 0


class TestBudgetEnforcement:
    def test_no_budget_never_over(self):
        t = TokenTracker(budget_tokens=0)
        t.record(_result("a", 10_000, 10_000))
        assert t.is_over_budget() is False

    def test_within_budget_not_over(self):
        t = TokenTracker(budget_tokens=1000)
        t.record(_result("a", 400, 400))
        assert t.is_over_budget() is False

    def test_exact_budget_not_over(self):
        t = TokenTracker(budget_tokens=1000)
        t.record(_result("a", 500, 500))
        assert t.is_over_budget() is False

    def test_exceeds_budget(self):
        t = TokenTracker(budget_tokens=500)
        t.record(_result("a", 300, 300))
        assert t.is_over_budget() is True

    def test_remaining_budget_correct(self):
        t = TokenTracker(budget_tokens=1000)
        t.record(_result("a", 300, 200))
        assert t.remaining_budget() == 500

    def test_remaining_budget_capped_at_zero(self):
        t = TokenTracker(budget_tokens=100)
        t.record(_result("a", 200, 200))
        assert t.remaining_budget() == 0

    def test_unlimited_budget_returns_negative_one(self):
        t = TokenTracker(budget_tokens=0)
        assert t.remaining_budget() == -1


class TestCostEstimation:
    def test_ollama_is_free(self):
        t = TokenTracker(provider="ollama")
        t.record(_result("a", 10_000, 10_000))
        assert t.summary().estimated_cost_usd == 0.0

    def test_openai_has_cost(self):
        t = TokenTracker(provider="openai")
        t.record(_result("a", 1000, 1000))
        s = t.summary()
        assert s.estimated_cost_usd > 0

    def test_anthropic_has_cost(self):
        t = TokenTracker(provider="anthropic")
        t.record(_result("a", 1000, 1000))
        assert t.summary().estimated_cost_usd > 0

    def test_unknown_provider_defaults_to_free(self):
        t = TokenTracker(provider="unknown_xyz")
        t.record(_result("a", 1000, 1000))
        assert t.summary().estimated_cost_usd == 0.0

    def test_cost_scales_with_tokens(self):
        t1 = TokenTracker(provider="openai")
        t2 = TokenTracker(provider="openai")
        t1.record(_result("a", 1000, 1000))
        t2.record(_result("a", 2000, 2000))
        assert t2.summary().estimated_cost_usd > t1.summary().estimated_cost_usd


class TestTokenUsageSummaryStr:
    def test_str_shows_tokens(self):
        t = TokenTracker(provider="ollama")
        t.record(_result("a", 100, 200))
        s = str(t.summary())
        assert "300" in s

    def test_str_shows_free_for_local(self):
        t = TokenTracker(provider="ollama")
        t.record(_result("a", 100, 200))
        s = str(t.summary())
        assert "free" in s.lower()

    def test_str_shows_cost_for_cloud(self):
        t = TokenTracker(provider="openai")
        t.record(_result("a", 1000, 1000))
        s = str(t.summary())
        assert "$" in s
