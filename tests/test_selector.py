"""Tests for the smart agent selector (dynamic, context-driven agent selection)."""
from __future__ import annotations

import pytest

from nexarq_cli.agents.registry import REGISTRY
from nexarq_cli.agents.selector import AgentSelector
from nexarq_cli.config.schema import NexarqConfig
from nexarq_cli.git.diff import DiffResult, FileDiff


def _diff(**kwargs) -> DiffResult:
    defaults = dict(
        commit_hash="abc", commit_message="test commit",
        files=[], total_added=0, total_removed=0,
        branch="main", author="alice", change_type="general",
        all_languages=[], repo_ecosystems={},
    )
    defaults.update(kwargs)
    return DiffResult(**defaults)


def _selector() -> AgentSelector:
    return AgentSelector(REGISTRY, NexarqConfig())


class TestSelectorExplicitAgents:
    def test_explicit_agents_returned_as_is(self):
        sel = _selector()
        diff = _diff()
        priority, parallel = sel.select(diff, requested=["security", "review"])
        all_agents = priority + parallel
        assert set(all_agents) == {"security", "review"}

    def test_critical_agent_in_priority(self):
        sel = _selector()
        diff = _diff()
        priority, parallel = sel.select(diff, requested=["security", "review"])
        assert "security" in priority
        assert "review" in parallel

    def test_high_severity_in_priority(self):
        sel = _selector()
        diff = _diff()
        priority, parallel = sel.select(diff, requested=["bugs", "style"])
        assert "bugs" in priority
        assert "style" in parallel

    def test_disabled_agent_excluded(self):
        from nexarq_cli.config.schema import AgentConfig
        cfg = NexarqConfig()
        cfg.agents["review"] = AgentConfig(enabled=False)
        sel = AgentSelector(REGISTRY, cfg)
        diff = _diff()
        priority, parallel = sel.select(diff, requested=["security", "review"])
        all_agents = priority + parallel
        assert "review" not in all_agents
        assert "security" in all_agents


class TestSelectorAutoSelection:
    def test_security_files_trigger_security_agents(self):
        files = [FileDiff("src/auth/login.py", "python", 10, 0, "")]
        diff = _diff(files=files, change_type="general")
        sel = _selector()
        priority, parallel = sel.select(diff)
        all_agents = priority + parallel
        assert "security" in all_agents or "secrets_detection" in all_agents

    def test_bug_fix_commit_triggers_bug_agents(self):
        diff = _diff(change_type="bug_fix", files=[
            FileDiff("src/main.py", "python", 5, 3, "")
        ])
        sel = _selector()
        priority, parallel = sel.select(diff)
        all_agents = priority + parallel
        assert "bugs" in all_agents or "error_handling" in all_agents

    def test_sql_migration_triggers_database(self):
        files = [FileDiff("db/migrations/001.sql", "sql", 20, 0, "")]
        diff = _diff(files=files, change_type="database_change")
        sel = _selector()
        priority, parallel = sel.select(diff)
        all_agents = priority + parallel
        assert "database" in all_agents

    def test_new_files_trigger_docstring(self):
        files = [FileDiff("src/new_module.py", "python", 50, 0, "", is_new_file=True)]
        diff = _diff(files=files, change_type="new_feature")
        sel = _selector()
        priority, parallel = sel.select(diff)
        all_agents = priority + parallel
        assert "docstring" in all_agents or "style" in all_agents

    def test_test_files_trigger_coverage(self):
        files = [FileDiff("tests/test_auth.py", "python", 15, 0, "")]
        diff = _diff(files=files)
        sel = _selector()
        priority, parallel = sel.select(diff)
        all_agents = priority + parallel
        assert "test_coverage" in all_agents

    def test_large_diff_triggers_risk_scoring(self):
        files = [FileDiff("src/big.py", "python", 100, 50, "")]
        diff = _diff(files=files, total_added=100, total_removed=50)
        sel = _selector()
        priority, parallel = sel.select(diff)
        all_agents = priority + parallel
        assert "risk_scoring" in all_agents or "summary" in all_agents

    def test_review_always_included_with_files(self):
        files = [FileDiff("src/x.py", "python", 3, 1, "")]
        diff = _diff(files=files)
        sel = _selector()
        priority, parallel = sel.select(diff)
        all_agents = priority + parallel
        assert "review" in all_agents

    def test_security_agents_in_priority_batch(self):
        files = [FileDiff("auth.py", "python", 5, 0, "")]
        diff = _diff(files=files, change_type="security")
        sel = _selector()
        priority, parallel = sel.select(diff)
        assert "security" in priority or "secrets_detection" in priority

    def test_no_unknown_agents_selected(self):
        """Selector never picks agents not in the registry."""
        files = [FileDiff("main.py", "python", 10, 5, "")]
        diff = _diff(files=files, change_type="new_feature", total_added=30, total_removed=5)
        sel = _selector()
        priority, parallel = sel.select(diff)
        known = set(REGISTRY.names())
        for name in priority + parallel:
            assert name in known, f"Unknown agent '{name}' selected"

    def test_no_duplicate_agents(self):
        files = [FileDiff("auth.py", "python", 50, 10, "", is_new_file=True)]
        diff = _diff(files=files, change_type="new_feature",
                     total_added=50, total_removed=10)
        sel = _selector()
        priority, parallel = sel.select(diff)
        all_agents = priority + parallel
        assert len(all_agents) == len(set(all_agents)), "Duplicate agents detected"

    def test_severity_split_correct(self):
        """_split_by_severity puts CRITICAL/HIGH in priority, others in parallel."""
        sel = _selector()
        priority, parallel = sel._split_by_severity(["security", "bugs", "style", "summary"])
        assert "security" in priority   # CRITICAL
        assert "bugs" in priority       # HIGH
        assert "style" in parallel      # LOW
        assert "summary" in parallel    # INFO
