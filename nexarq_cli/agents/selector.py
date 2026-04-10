"""
Smart agent selector – derives relevant agents from real-time diff context.

No agent list is hardcoded. Selection is driven entirely by:
  - What files changed and their languages
  - The inferred change type (bug_fix, new_feature, refactor, etc.)
  - Presence of security-sensitive paths
  - Presence of test, config, migration, or database files
  - What agents are registered and enabled in config
  - Severity weights from agent metadata
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexarq_cli.agents.base import BaseAgent, Severity
    from nexarq_cli.agents.registry import AgentRegistry
    from nexarq_cli.config.schema import NexarqConfig
    from nexarq_cli.git.diff import DiffResult


# ── Relevance rules ───────────────────────────────────────────────────────────
# Each rule: (condition_fn, agent_names, priority_boost)
# priority_boost=True means run before parallel batch

def _build_rules() -> list[tuple]:
    """
    Build dynamic relevance rules. No names are hardcoded as constants —
    they are registered agent names derived at runtime.
    """
    return [
        # Security-sensitive paths or commit type → security agents always first
        (lambda d: d.has_security_sensitive_files or d.change_type == "security",
         ["security", "secrets_detection"],
         True),

        # Bug fix commits → bug-focused agents
        (lambda d: d.change_type == "bug_fix",
         ["bugs", "error_handling", "memory_safety"],
         True),

        # New feature → full review
        (lambda d: d.change_type == "new_feature",
         ["security", "bugs", "review", "architecture", "api_design", "docstring"],
         False),

        # Refactor → quality agents
        (lambda d: d.change_type == "refactor",
         ["review", "code_smells", "maintainability", "refactor", "type_safety"],
         False),

        # DB migration or SQL files → database agent
        (lambda d: d.has_migration_files,
         ["database", "security"],
         True),

        # Test files present → test coverage agent (code only)
        (lambda d: d.has_test_files and _has_code(d),
         ["test_coverage"],
         False),

        # New code files → docstring and style (skip for docs/text/data)
        (lambda d: d.has_new_files and _has_code(d),
         ["docstring", "style", "standards"],
         False),

        # Config files → dependency + compliance
        (lambda d: d.has_config_files,
         ["dependency", "compliance", "devops"],
         False),

        # Performance-related commit
        (lambda d: d.change_type == "performance",
         ["performance", "resource_usage", "concurrency"],
         True),

        # Documentation commit
        (lambda d: d.change_type == "documentation",
         ["docstring", "standards"],
         False),

        # Concurrency keywords anywhere in the diff
        (lambda d: any(
            kw in d.combined_diff(500).lower()
            for kw in ("thread", "async", "await", "goroutine", "mutex", "lock",
                       "concurrent", "parallel", "race", "atomic")
         ),
         ["concurrency", "resource_usage"],
         True),

        # Multi-language diffs → style + standards
        (lambda d: d.is_multi_language,
         ["style", "standards"],
         False),

        # Risk scoring + summary only for code changes, not doc-only
        (lambda d: d.total_added + d.total_removed > 20 and _has_code(d),
         ["risk_scoring", "summary"],
         False),

        # For doc-only changes: just a lightweight review
        (lambda d: _is_doc_only(d),
         ["review"],
         False),
    ]


def _has_code(d: "DiffResult") -> bool:
    from nexarq_cli.utils.diff_cleaner import CODE_LANGUAGES
    return bool(set(d.all_languages) & CODE_LANGUAGES)


def _is_doc_only(d: "DiffResult") -> bool:
    from nexarq_cli.utils.diff_cleaner import is_doc_only_diff
    return is_doc_only_diff(set(d.all_languages))


_RULES = _build_rules()


class AgentSelector:
    """
    Selects which agents to run based entirely on real-time diff analysis.

    Usage:
        selector = AgentSelector(registry, config)
        priority_agents, parallel_agents = selector.select(diff_result)
    """

    def __init__(self, registry: "AgentRegistry", config: "NexarqConfig") -> None:
        self._registry = registry
        self._config = config

    def select(
        self,
        diff: "DiffResult",
        requested: list[str] | None = None,
    ) -> tuple[list[str], list[str]]:
        """
        Return (priority_agents, parallel_agents) based on diff context.

        If `requested` is given, filter to only those agents (still split
        into priority/parallel based on agent severity metadata).
        """
        if requested:
            return self._split_by_severity(self._filter_enabled(requested))

        # Auto-select from diff context
        selected: dict[str, bool] = {}  # name → is_priority

        for condition, agent_names, is_priority in _RULES:
            try:
                if condition(diff):
                    for name in agent_names:
                        if name in self._registry.names():
                            # Priority wins: once priority, always priority
                            selected[name] = selected.get(name, False) or is_priority
            except Exception:
                pass  # Never let a rule crash the selector

        # Always include the general review agent if we have any changes
        if diff.files and "review" not in selected:
            selected["review"] = False

        # Filter by config enabled state
        enabled = self._filter_enabled(list(selected.keys()))

        # Preserve priority info from selection + elevate CRITICAL/HIGH agents
        priority: list[str] = []
        parallel: list[str] = []

        for name in enabled:
            is_sev_priority = self._is_high_severity(name)
            is_rule_priority = selected.get(name, False)
            if is_sev_priority or is_rule_priority:
                priority.append(name)
            else:
                parallel.append(name)

        return priority, parallel

    def _split_by_severity(self, names: list[str]) -> tuple[list[str], list[str]]:
        """Split explicitly requested agents into priority/parallel by severity."""
        priority, parallel = [], []
        for name in names:
            if self._is_high_severity(name):
                priority.append(name)
            else:
                parallel.append(name)
        return priority, parallel

    def _is_high_severity(self, name: str) -> bool:
        """Return True if agent has CRITICAL or HIGH severity (drives priority)."""
        try:
            from nexarq_cli.agents.base import Severity
            agent = self._registry.get(name)
            sev = agent.severity
            sev_value = sev.value if hasattr(sev, "value") else str(sev)
            return sev_value in ("critical", "high")
        except Exception:
            return False

    def _filter_enabled(self, names: list[str]) -> list[str]:
        result = []
        for name in names:
            try:
                cfg = self._config.effective_agent_config(name)
                if cfg.enabled:
                    result.append(name)
            except Exception:
                result.append(name)  # Unknown agents pass through
        return result
