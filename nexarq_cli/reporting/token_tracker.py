"""Token usage tracking and cost estimation (SRS 3.11)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexarq_cli.agents.base import AgentResult

# Fallback rates — overridden by config.token_budget.cost_rates at runtime
_DEFAULT_COST_PER_1K: dict[str, dict[str, float]] = {
    "openai":    {"prompt": 0.003,  "completion": 0.006},
    "anthropic": {"prompt": 0.003,  "completion": 0.015},
    "google":    {"prompt": 0.002,  "completion": 0.006},
    "ollama":    {"prompt": 0.0,    "completion": 0.0},
    "mock":      {"prompt": 0.0,    "completion": 0.0},
}


@dataclass
class TokenUsageSummary:
    total_prompt: int = 0
    total_completion: int = 0
    total_tokens: int = 0
    by_agent: dict[str, dict[str, int]] = field(default_factory=dict)
    estimated_cost_usd: float = 0.0
    provider: str = "ollama"

    def __str__(self) -> str:
        cost_str = f"${self.estimated_cost_usd:.4f}" if self.estimated_cost_usd > 0 else "free (local)"
        return (
            f"Tokens: {self.total_tokens} "
            f"(prompt={self.total_prompt}, completion={self.total_completion}) | "
            f"Est. cost: {cost_str}"
        )


class TokenTracker:
    """
    Accumulate token usage across all agent runs and compute cost estimates.

    SRS 3.11: Track usage, enforce limits, provide cost visibility.
    Rates are taken from config.token_budget.cost_rates when provided,
    falling back to _DEFAULT_COST_PER_1K.
    """

    def __init__(
        self,
        provider: str = "ollama",
        budget_tokens: int = 0,
        cost_rates: dict | None = None,
    ) -> None:
        self._provider = provider.lower()
        self._budget_tokens = budget_tokens  # 0 = unlimited
        self._rates = cost_rates or _DEFAULT_COST_PER_1K
        self._total_prompt = 0
        self._total_completion = 0
        self._by_agent: dict[str, dict[str, int]] = {}

    def record(self, result: "AgentResult") -> None:
        """Record token usage from an agent result."""
        prompt = result.token_usage.get("prompt", 0)
        completion = result.token_usage.get("completion", 0)
        self._total_prompt += prompt
        self._total_completion += completion
        self._by_agent[result.agent_name] = {"prompt": prompt, "completion": completion}

    def is_over_budget(self) -> bool:
        """Return True if token budget is exceeded (0 = unlimited)."""
        if self._budget_tokens <= 0:
            return False
        return (self._total_prompt + self._total_completion) > self._budget_tokens

    def remaining_budget(self) -> int:
        """Remaining token budget (0 = unlimited)."""
        if self._budget_tokens <= 0:
            return -1
        return max(0, self._budget_tokens - self._total_prompt - self._total_completion)

    def summary(self) -> TokenUsageSummary:
        """Return aggregated usage summary."""
        total = self._total_prompt + self._total_completion
        rates = self._rates.get(self._provider, {"prompt": 0.0, "completion": 0.0})
        cost = (
            self._total_prompt / 1000 * rates["prompt"]
            + self._total_completion / 1000 * rates["completion"]
        )
        return TokenUsageSummary(
            total_prompt=self._total_prompt,
            total_completion=self._total_completion,
            total_tokens=total,
            by_agent=dict(self._by_agent),
            estimated_cost_usd=round(cost, 6),
            provider=self._provider,
        )
