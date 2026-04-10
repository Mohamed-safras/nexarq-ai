"""
Tests for the 8 new agents:
i18n, risk_scoring, summary, code_smells, secrets_detection, ai_fixes, style, resource_usage
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from nexarq_cli.agents.base import AgentResult, AgentPermissions, Severity
from nexarq_cli.agents.registry import REGISTRY
from nexarq_cli.llm.base import LLMResponse


# ── Mock provider ─────────────────────────────────────────────────────────────

class _MockProvider:
    name = "mock"
    model = "test"

    def complete(self, prompt: str, system: str = "") -> LLMResponse:
        return LLMResponse(
            text="SEVERITY: MEDIUM\nFINDING: Test finding\nFIX: Test fix",
            provider="mock",
            model="test",
            prompt_tokens=50,
            completion_tokens=100,
        )

    def health_check(self) -> bool:
        return True


MOCK_DIFF = """\
diff --git a/auth.py b/auth.py
--- a/auth.py
+++ b/auth.py
@@ -1,5 +1,8 @@
+API_KEY = "sk-1234567890abcdef"
+DB_PASSWORD = "supersecret123"
+
 def login(user, password):
-    return check(user, password)
+    query = f"SELECT * FROM users WHERE user='{user}'"
+    return db.execute(query)
"""


# ── Registry: all 30 agents registered ───────────────────────────────────────

class TestRegistryCompleteness:
    EXPECTED_NEW = {
        "i18n", "risk_scoring", "summary", "code_smells",
        "secrets_detection", "ai_fixes", "style", "resource_usage",
    }
    EXPECTED_ORIGINAL = {
        "security", "bugs", "performance", "review", "architecture",
        "devops", "refactor", "docstring", "type_safety", "test_coverage",
        "dependency", "api_design", "database", "concurrency", "error_handling",
        "logging", "maintainability", "accessibility", "compliance",
        "explain", "memory_safety", "standards",
    }

    def test_all_new_agents_registered(self):
        names = set(REGISTRY.names())
        missing = self.EXPECTED_NEW - names
        assert not missing, f"Missing new agents: {missing}"

    def test_all_original_agents_still_registered(self):
        names = set(REGISTRY.names())
        missing = self.EXPECTED_ORIGINAL - names
        assert not missing, f"Missing original agents: {missing}"

    def test_total_agent_count(self):
        assert len(REGISTRY.names()) == 30

    def test_all_agents_instantiable(self):
        for name in REGISTRY.names():
            agent = REGISTRY.get(name)
            assert agent is not None
            assert agent.name == name


# ── i18n agent ────────────────────────────────────────────────────────────────

class TestI18nAgent:
    def test_registered(self):
        assert "i18n" in REGISTRY.names()

    def test_severity_medium(self):
        agent = REGISTRY.get("i18n")
        assert agent.severity == Severity.MEDIUM

    def test_diff_only_permissions(self):
        agent = REGISTRY.get("i18n")
        assert agent.permissions.read_diff_only is True
        assert agent.permissions.execute_code is False

    def test_prompt_contains_diff(self):
        agent = REGISTRY.get("i18n")
        prompt = agent.build_prompt(MOCK_DIFF, "python")
        assert MOCK_DIFF in prompt

    def test_prompt_mentions_i18n_topics(self):
        agent = REGISTRY.get("i18n")
        prompt = agent.build_prompt(MOCK_DIFF, "python")
        assert "locale" in prompt.lower() or "i18n" in prompt.lower()

    def test_run_returns_result(self):
        agent = REGISTRY.get("i18n")
        result = agent.run(MOCK_DIFF, "python", _MockProvider())
        assert isinstance(result, AgentResult)
        assert result.agent_name == "i18n"


# ── risk_scoring agent ────────────────────────────────────────────────────────

class TestRiskScoringAgent:
    def test_registered(self):
        assert "risk_scoring" in REGISTRY.names()

    def test_severity_high(self):
        assert REGISTRY.get("risk_scoring").severity == Severity.HIGH

    def test_prompt_contains_scoring_dimensions(self):
        agent = REGISTRY.get("risk_scoring")
        prompt = agent.build_prompt(MOCK_DIFF, "python")
        assert "Security Risk" in prompt
        assert "Reliability" in prompt
        assert "Risk Score" in prompt

    def test_run_returns_result(self):
        agent = REGISTRY.get("risk_scoring")
        result = agent.run(MOCK_DIFF, "python", _MockProvider())
        assert result.success


# ── summary agent ─────────────────────────────────────────────────────────────

class TestSummaryAgent:
    def test_registered(self):
        assert "summary" in REGISTRY.names()

    def test_severity_info(self):
        assert REGISTRY.get("summary").severity == Severity.INFO

    def test_prompt_contains_summary_sections(self):
        agent = REGISTRY.get("summary")
        prompt = agent.build_prompt(MOCK_DIFF, "python")
        assert "Recommendation" in prompt
        assert "APPROVE" in prompt or "BLOCK" in prompt

    def test_run_returns_result(self):
        agent = REGISTRY.get("summary")
        result = agent.run(MOCK_DIFF, "python", _MockProvider())
        assert isinstance(result, AgentResult)


# ── code_smells agent ─────────────────────────────────────────────────────────

class TestCodeSmellsAgent:
    def test_registered(self):
        assert "code_smells" in REGISTRY.names()

    def test_severity_medium(self):
        assert REGISTRY.get("code_smells").severity == Severity.MEDIUM

    def test_prompt_mentions_patterns(self):
        agent = REGISTRY.get("code_smells")
        prompt = agent.build_prompt(MOCK_DIFF, "python")
        assert "God Object" in prompt or "Duplicate" in prompt or "Long method" in prompt.replace("Long methods", "Long method")

    def test_run_returns_result(self):
        agent = REGISTRY.get("code_smells")
        result = agent.run(MOCK_DIFF, "python", _MockProvider())
        assert result.agent_name == "code_smells"


# ── secrets_detection agent ───────────────────────────────────────────────────

class TestSecretsDetectionAgent:
    def test_registered(self):
        assert "secrets_detection" in REGISTRY.names()

    def test_severity_critical(self):
        assert REGISTRY.get("secrets_detection").severity == Severity.CRITICAL

    def test_prompt_covers_secret_types(self):
        agent = REGISTRY.get("secrets_detection")
        prompt = agent.build_prompt(MOCK_DIFF, "python")
        assert "API Key" in prompt or "api key" in prompt.lower()
        assert "Private Key" in prompt or "private key" in prompt.lower()

    def test_prompt_warns_not_to_reproduce_secrets(self):
        agent = REGISTRY.get("secrets_detection")
        prompt = agent.build_prompt(MOCK_DIFF, "python")
        assert "do NOT reproduce" in prompt or "NOT reproduce" in prompt

    def test_run_returns_result(self):
        agent = REGISTRY.get("secrets_detection")
        result = agent.run(MOCK_DIFF, "python", _MockProvider())
        assert isinstance(result, AgentResult)


# ── ai_fixes agent ────────────────────────────────────────────────────────────

class TestAIFixesAgent:
    def test_registered(self):
        assert "ai_fixes" in REGISTRY.names()

    def test_severity_high(self):
        assert REGISTRY.get("ai_fixes").severity == Severity.HIGH

    def test_prompt_requests_before_after(self):
        agent = REGISTRY.get("ai_fixes")
        prompt = agent.build_prompt(MOCK_DIFF, "python")
        assert "Before:" in prompt
        assert "After:" in prompt

    def test_run_returns_result(self):
        agent = REGISTRY.get("ai_fixes")
        result = agent.run(MOCK_DIFF, "python", _MockProvider())
        assert result.success


# ── style agent ───────────────────────────────────────────────────────────────

class TestStyleAgent:
    def test_registered(self):
        assert "style" in REGISTRY.names()

    def test_severity_low(self):
        assert REGISTRY.get("style").severity == Severity.LOW

    def test_prompt_covers_naming(self):
        agent = REGISTRY.get("style")
        prompt = agent.build_prompt(MOCK_DIFF, "python")
        assert "naming" in prompt.lower() or "Naming" in prompt

    def test_run_returns_result(self):
        agent = REGISTRY.get("style")
        result = agent.run(MOCK_DIFF, "python", _MockProvider())
        assert isinstance(result, AgentResult)


# ── resource_usage agent ──────────────────────────────────────────────────────

class TestResourceUsageAgent:
    def test_registered(self):
        assert "resource_usage" in REGISTRY.names()

    def test_severity_high(self):
        assert REGISTRY.get("resource_usage").severity == Severity.HIGH

    def test_prompt_covers_memory_cpu_io(self):
        agent = REGISTRY.get("resource_usage")
        prompt = agent.build_prompt(MOCK_DIFF, "python")
        assert "Memory" in prompt or "memory" in prompt
        assert "CPU" in prompt or "cpu" in prompt.lower()
        assert "I/O" in prompt or "file handle" in prompt.lower()

    def test_run_returns_result(self):
        agent = REGISTRY.get("resource_usage")
        result = agent.run(MOCK_DIFF, "python", _MockProvider())
        assert result.agent_name == "resource_usage"

    def test_execute_code_always_false(self):
        for name in REGISTRY.names():
            agent = REGISTRY.get(name)
            assert agent.permissions.execute_code is False, (
                f"Agent '{name}' has execute_code=True – this violates SEC-7/8"
            )
