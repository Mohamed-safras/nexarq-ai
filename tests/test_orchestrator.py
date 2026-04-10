"""
Scenarios: orchestrator parallel execution, priority ordering,
           cloud consent blocking, agent filtering, redaction gate,
           disabled agents skipped.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nexarq_cli.agents.base import AgentResult, Severity
from nexarq_cli.agents.orchestrator import AgentOrchestrator
from nexarq_cli.agents.registry import REGISTRY
from nexarq_cli.config.schema import NexarqConfig, ProviderConfig, ProviderName
from nexarq_cli.llm.base import BaseLLMProvider, LLMResponse
from nexarq_cli.llm.factory import LLMFactory
from nexarq_cli.security.secrets import SecretsManager


# ── Mock provider ─────────────────────────────────────────────────────────────

class _MockProvider(BaseLLMProvider):
    name = "mock"
    def _call_api(self, prompt, system=""):
        return LLMResponse(
            text=f"Mock analysis for: {prompt[:30]}",
            provider="mock", model="mock",
            prompt_tokens=10, completion_tokens=50,
        )
    def health_check(self): return True


def _make_orchestrator(cloud_consent=False, disabled_agents=None):
    cfg = NexarqConfig()
    cfg.privacy.cloud_consent = cloud_consent
    cfg.providers["default"] = ProviderConfig(name=ProviderName.OLLAMA)

    if disabled_agents:
        from nexarq_cli.config.schema import AgentConfig
        for name in disabled_agents:
            cfg.agents[name] = AgentConfig(enabled=False)

    secrets = SecretsManager()
    factory = LLMFactory(cfg, secrets)

    with patch.object(factory, "get", return_value=_MockProvider(model="mock")):
        with patch.object(factory, "get_for_agent", return_value=_MockProvider(model="mock")):
            orch = AgentOrchestrator(config=cfg, factory=factory, registry=REGISTRY)
            orch._factory = factory
    return orch, factory, cfg


SAMPLE_DIFF = """\
diff --git a/app.py b/app.py
@@ -1,3 +1,5 @@
+import os
+password = os.environ.get('DB_PASS', 'hardcoded')
 def connect():
-    pass
+    return db.connect(password)
"""


class TestOrchestratorBasic:
    def test_run_returns_results(self):
        orch, factory, cfg = _make_orchestrator()
        with patch.object(factory, "get_for_agent", return_value=_MockProvider(model="mock")):
            results = orch.run(SAMPLE_DIFF, "python", ["review"])
        assert len(results) == 1
        assert results[0].agent_name == "review"

    def test_stream_yields_results(self):
        orch, factory, cfg = _make_orchestrator()
        with patch.object(factory, "get_for_agent", return_value=_MockProvider(model="mock")):
            results = list(orch.stream(SAMPLE_DIFF, "python", ["review", "bugs"]))
        assert len(results) == 2

    def test_explicit_agents_run(self):
        """When explicit agent names are given, only those agents run."""
        orch, factory, cfg = _make_orchestrator()
        requested = ["security", "bugs", "review"]
        with patch.object(factory, "get_for_agent", return_value=_MockProvider(model="mock")):
            results = orch.run(SAMPLE_DIFF, "python", requested)
        agent_names = {r.agent_name for r in results}
        assert agent_names == set(requested)

    def test_result_has_output(self):
        orch, factory, cfg = _make_orchestrator()
        with patch.object(factory, "get_for_agent", return_value=_MockProvider(model="mock")):
            results = orch.run(SAMPLE_DIFF, "python", ["security"])
        assert results[0].output != "" or results[0].error is not None


class TestOrchestratorDisabledAgents:
    def test_disabled_agent_is_skipped(self):
        orch, factory, cfg = _make_orchestrator(disabled_agents=["review"])
        with patch.object(factory, "get_for_agent", return_value=_MockProvider(model="mock")):
            results = orch.run(SAMPLE_DIFF, "python", ["review", "bugs"])
        names = [r.agent_name for r in results]
        assert "review" not in names
        assert "bugs" in names

    def test_all_disabled_returns_empty(self):
        orch, factory, cfg = _make_orchestrator(disabled_agents=["security", "bugs"])
        with patch.object(factory, "get_for_agent", return_value=_MockProvider(model="mock")):
            results = orch.run(SAMPLE_DIFF, "python", ["security", "bugs"])
        assert results == []


class TestOrchestratorCloudConsent:
    def test_cloud_provider_blocked_without_consent(self):
        cfg = NexarqConfig()
        cfg.privacy.cloud_consent = False
        cfg.providers["default"] = ProviderConfig(name=ProviderName.OPENAI, model="gpt-4o")
        factory = LLMFactory(cfg, SecretsManager())

        orch = AgentOrchestrator(config=cfg, factory=factory, registry=REGISTRY)
        with patch.object(factory, "get_for_agent", return_value=_MockProvider(model="mock")):
            results = orch.run(SAMPLE_DIFF, "python", ["review"])

        # Should return an error result, not crash
        assert len(results) == 1
        assert results[0].error is not None
        assert "cloud_consent" in results[0].error

    def test_cloud_provider_allowed_with_consent(self):
        cfg = NexarqConfig()
        cfg.privacy.cloud_consent = True
        cfg.providers["default"] = ProviderConfig(name=ProviderName.OPENAI, model="gpt-4o")
        factory = LLMFactory(cfg, SecretsManager())

        orch = AgentOrchestrator(config=cfg, factory=factory, registry=REGISTRY)
        with patch.object(factory, "get_for_agent", return_value=_MockProvider(model="mock")):
            results = orch.run(SAMPLE_DIFF, "python", ["review"])

        assert results[0].error is None


class TestOrchestratorRedaction:
    def test_secrets_redacted_before_agents_see_diff(self):
        """SEC-6: diff must be redacted before reaching agents."""
        orch, factory, cfg = _make_orchestrator()
        sensitive_diff = SAMPLE_DIFF + '\napi_key = "sk-supersecretkey12345678"'

        captured_prompts = []

        class _CapturingProvider(_MockProvider):
            def _call_api(self, prompt, system=""):
                captured_prompts.append(prompt)
                return super()._call_api(prompt, system)

        with patch.object(factory, "get_for_agent", return_value=_CapturingProvider(model="mock")):
            orch.run(sensitive_diff, "python", ["review"])

        # The secret must not appear raw in any agent prompt
        for p in captured_prompts:
            assert "sk-supersecretkey12345678" not in p


class TestOrchestratorPriority:
    def test_priority_derived_from_severity(self):
        """Priority is driven by agent severity metadata, not a hardcoded set."""
        from nexarq_cli.agents.registry import REGISTRY
        from nexarq_cli.agents.base import Severity
        # CRITICAL/HIGH agents should be treated as priority
        for name in ["security", "secrets_detection", "bugs", "concurrency"]:
            agent = REGISTRY.get(name)
            sev = agent.severity.value if hasattr(agent.severity, "value") else str(agent.severity)
            assert sev in ("critical", "high"), (
                f"Expected '{name}' to be CRITICAL or HIGH, got {sev}"
            )

    def test_non_priority_agents_run(self):
        orch, factory, cfg = _make_orchestrator()
        with patch.object(factory, "get_for_agent", return_value=_MockProvider(model="mock")):
            results = orch.run(SAMPLE_DIFF, "python", ["review", "docstring"])
        names = {r.agent_name for r in results}
        assert names == {"review", "docstring"}


class TestOrchestratorAuditLogging:
    def test_audit_logger_called_on_agent_run(self):
        from nexarq_cli.reporting.audit import AuditLogger
        mock_audit = MagicMock(spec=AuditLogger)

        cfg = NexarqConfig()
        factory = LLMFactory(cfg, SecretsManager())
        orch = AgentOrchestrator(
            config=cfg, factory=factory, registry=REGISTRY, audit=mock_audit
        )
        with patch.object(factory, "get_for_agent", return_value=_MockProvider(model="mock")):
            orch.run(SAMPLE_DIFF, "python", ["review"])

        mock_audit.log_agent_run.assert_called_once()
