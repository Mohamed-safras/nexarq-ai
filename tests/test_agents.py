"""Tests for agent registry, base agent, and built-in agents."""
import pytest

from nexarq_cli.agents.base import BaseAgent, AgentResult, AgentPermissions, Severity
from nexarq_cli.agents.registry import REGISTRY


class TestAgentRegistry:
    def test_all_agents_registered(self):
        names = REGISTRY.names()
        assert len(names) == 30  # 22 original + 8 new (SRS 3.7 full coverage)

    def test_required_agents_present(self):
        # Original 22 agents
        original = {
            "security", "bugs", "performance", "review",
            "architecture", "devops", "refactor", "docstring",
            "type_safety", "test_coverage", "dependency", "api_design",
            "database", "concurrency", "error_handling", "logging",
            "maintainability", "accessibility", "compliance",
            "explain", "memory_safety", "standards",
        }
        # New 8 agents (SRS 3.7)
        new_agents = {
            "i18n", "risk_scoring", "summary", "code_smells",
            "secrets_detection", "ai_fixes", "style", "resource_usage",
        }
        required = original | new_agents
        assert required == set(REGISTRY.names())

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown agent"):
            REGISTRY.get("nonexistent")

    def test_all_agents_instantiate(self):
        for name in REGISTRY.names():
            agent = REGISTRY.get(name)
            assert isinstance(agent, BaseAgent)

    def test_all_agents_have_no_execute_permission(self):
        """SEC-7/8: No agent may ever execute code."""
        for name in REGISTRY.names():
            agent = REGISTRY.get(name)
            assert agent.permissions.execute_code is False, (
                f"Agent '{name}' has execute_code=True – security violation!"
            )

    def test_all_agents_default_to_diff_only(self):
        """AG-3: All agents default to diff-only access."""
        for name in REGISTRY.names():
            agent = REGISTRY.get(name)
            assert agent.permissions.read_diff_only is True, (
                f"Agent '{name}' does not default to diff-only"
            )

    def test_descriptions_non_empty(self):
        for name, desc in REGISTRY.descriptions().items():
            assert desc, f"Agent '{name}' has no description"

    def test_security_agent_is_critical(self):
        agent = REGISTRY.get("security")
        assert agent.severity == Severity.CRITICAL

    def test_compliance_agent_is_critical(self):
        agent = REGISTRY.get("compliance")
        assert agent.severity == Severity.CRITICAL

    def test_concurrency_agent_is_critical(self):
        agent = REGISTRY.get("concurrency")
        assert agent.severity == Severity.CRITICAL


class TestAgentPrompts:
    """Verify each agent builds a non-empty prompt."""

    SAMPLE_DIFF = """\
diff --git a/app.py b/app.py
@@ -1,5 +1,8 @@
+import os
+password = os.environ.get("DB_PASS", "hardcoded_password")
+
 def connect():
-    pass
+    return db.connect(password)
"""

    def test_all_agents_build_prompt(self):
        for name in REGISTRY.names():
            agent = REGISTRY.get(name)
            prompt = agent.build_prompt(self.SAMPLE_DIFF, "python")
            assert isinstance(prompt, str)
            assert len(prompt) > 10, f"Agent '{name}' built an empty prompt"

    def test_standards_agent_skips_without_context(self):
        from nexarq_cli.agents.builtin.standards import StandardsAgent
        agent = StandardsAgent()
        result = agent.run(self.SAMPLE_DIFF, "python", provider=None)  # type: ignore
        assert "No project coding standards" in result.output
        assert result.success is True
