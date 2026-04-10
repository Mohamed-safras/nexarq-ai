"""
Tiered agent execution — cost vs depth trade-off.

Tier 1  FAST    Always runs. 3 agents. Catches secrets + critical issues.
                Cost: ~3 LLM calls per commit.

Tier 2  SMART   Diff-context selected. Runs only agents relevant to the change.
                Skips irrelevant agents (e.g. i18n on a backend diff).
                Cost: ~5-12 LLM calls per commit.

Tier 3  DEEP    Tool-augmented agents. Runs ONLY when Tier 1/2 found
                CRITICAL or HIGH issues. Most expensive — justify the cost.
                Cost: +5-25 tool calls per CRITICAL issue.

Modes:
  fast   Run Tier 1 only  → cheapest, great for pre-push CI gates
  smart  Run Tier 1 + 2   → default, good balance (recommended)
  deep   Run all tiers    → full investigation every time
  auto   Tier 1 + 2, escalate to Tier 3 only if CRITICAL/HIGH found
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexarq_cli.agents.base import AgentResult
    from nexarq_cli.config.schema import ExecutionTierConfig, NexarqConfig
    from nexarq_cli.agents.registry import AgentRegistry
    from nexarq_cli.git.diff import DiffResult


# Tier 1: always run — fast, lightweight, no tools
_TIER1 = ["secrets_detection", "security", "bugs"]

# Tier 3: tool-augmented — only escalate to these
_TIER3 = ["security", "bugs", "concurrency", "memory_safety", "architecture"]


class TierPlanner:
    """
    Decides which agents to run and in which tier, given a diff and config.
    """

    def __init__(
        self,
        registry: "AgentRegistry",
        config: "NexarqConfig",
    ) -> None:
        self._registry = registry
        self._config = config
        self._tier_cfg = config.execution

    def plan(
        self,
        diff_result: "DiffResult | None",
        requested: list[str] | None = None,
    ) -> "TierPlan":
        """
        Return a TierPlan describing which agents run in which tier.
        If `requested` is given, restrict to those agents only.
        """
        from nexarq_cli.agents.selector import AgentSelector

        mode = self._tier_cfg.mode
        max_agents = self._tier_cfg.max_agents
        registered = set(self._registry.names())
        selector = AgentSelector(self._registry, self._config)

        # ── Tier 1 (always) ───────────────────────────────────────────────
        tier1 = [
            n for n in (self._tier_cfg.tier1_agents or _TIER1)
            if n in registered and self._agent_enabled(n)
            and (requested is None or n in requested)
        ]

        # ── Tier 2 (smart selection from diff) ────────────────────────────
        if diff_result is not None:
            priority, parallel = selector.select(diff_result, requested)
            smart_all = list(dict.fromkeys(priority + parallel))  # preserve order, dedup
        elif requested:
            smart_all = selector._filter_enabled(requested)
        else:
            defaults = self._config.default_agents or list(registered)
            smart_all = selector._filter_enabled(defaults)

        # Remove tier1 from tier2 to avoid duplicates
        tier1_set = set(tier1)
        tier2 = [n for n in smart_all if n not in tier1_set]

        # ── Tier 3 (tool-augmented, conditional) ──────────────────────────
        tier3 = [
            n for n in _TIER3
            if n in registered and self._agent_enabled(n)
            and (requested is None or n in requested)
        ]

        # ── Apply mode ────────────────────────────────────────────────────
        if mode == "fast":
            tier2, tier3 = [], []
        elif mode == "smart":
            tier3 = []
        elif mode == "deep":
            pass  # all tiers as-is
        elif mode == "auto":
            tier3 = []  # start without tier3; escalate later if needed

        # ── Apply max_agents cap ──────────────────────────────────────────
        if max_agents > 0:
            # Priority: tier1 > tier2, cap only tier2
            allowed_tier2 = max(0, max_agents - len(tier1))
            tier2 = tier2[:allowed_tier2]
            tier3 = []  # never auto-run tier3 under a hard cap

        return TierPlan(
            tier1=tier1,
            tier2=tier2,
            tier3=tier3,
            mode=mode,
            tool_budget=self._tier_cfg.max_tool_calls_per_agent,
            deep_trigger=self._tier_cfg.deep_trigger_severity,
        )

    def _agent_enabled(self, name: str) -> bool:
        try:
            return self._config.effective_agent_config(name).enabled
        except Exception:
            return True


class TierPlan:
    """Immutable execution plan produced by TierPlanner."""

    def __init__(
        self,
        tier1: list[str],
        tier2: list[str],
        tier3: list[str],
        mode: str,
        tool_budget: int,
        deep_trigger: str,
    ) -> None:
        self.tier1 = tier1
        self.tier2 = tier2
        self.tier3 = tier3
        self.mode = mode
        self.tool_budget = tool_budget
        self.deep_trigger = deep_trigger

    def should_escalate(self, results: list["AgentResult"]) -> bool:
        """
        Return True if Tier 3 should be triggered based on Tier 1/2 results.
        Only relevant in "auto" mode.
        """
        if self.mode != "auto":
            return False
        trigger_severities = {"critical"}
        if self.deep_trigger == "high":
            trigger_severities.add("high")
        for r in results:
            if r.error:
                continue
            sev = str(r.severity.value if hasattr(r.severity, "value") else r.severity)
            if sev in trigger_severities and r.output and len(r.output.strip()) > 20:
                return True
        return False

    def all_agents(self) -> list[str]:
        """All agents in execution order (no duplicates)."""
        seen: set[str] = set()
        out: list[str] = []
        for n in self.tier1 + self.tier2 + self.tier3:
            if n not in seen:
                seen.add(n)
                out.append(n)
        return out

    def __repr__(self) -> str:
        return (
            f"TierPlan(mode={self.mode!r}, "
            f"tier1={self.tier1}, tier2={self.tier2}, tier3={self.tier3})"
        )
