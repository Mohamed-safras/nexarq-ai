"""
End-to-end scenarios: full pipeline from diff → agents → results → interactive.
Uses a mock LLM provider so no real Ollama/API needed.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nexarq_cli.agents.base import AgentResult, Severity
from nexarq_cli.agents.orchestrator import AgentOrchestrator
from nexarq_cli.agents.registry import REGISTRY
from nexarq_cli.cli.interactive import InteractiveSession
from nexarq_cli.config.schema import NexarqConfig, ProviderConfig, ProviderName
from nexarq_cli.git.diff import DiffEngine
from nexarq_cli.llm.base import BaseLLMProvider, LLMResponse
from nexarq_cli.llm.factory import LLMFactory
from nexarq_cli.reporting.audit import AuditLogger
from nexarq_cli.reporting.formatter import ReportFormatter
from nexarq_cli.security.redaction import Redactor
from nexarq_cli.security.secrets import SecretsManager
from rich.console import Console


# ── Mock LLM provider ─────────────────────────────────────────────────────────

class MockLLMProvider(BaseLLMProvider):
    """Deterministic mock provider for E2E tests."""
    name = "mock"

    RESPONSES = {
        "security": "SEVERITY: HIGH\nLOCATION: auth.py:3\nVULNERABILITY: Hardcoded credential\nFIX: Use environment variables.",
        "bugs": "SEVERITY: MEDIUM\nLOCATION: auth.py:5\nCAUSE: Missing null check\nFIX: Add `if password is None: raise ValueError`",
        "review": "Issue 1: Variable `pwd` should be named `password` for clarity.",
        "performance": "No performance issues found.",
        "default": "No issues found.",
    }

    def _call_api(self, prompt: str, system: str = "") -> LLMResponse:
        for key, response in self.RESPONSES.items():
            if key in prompt.lower():
                return LLMResponse(text=response, provider="mock", model=self.model,
                                   prompt_tokens=100, completion_tokens=50)
        return LLMResponse(text=self.RESPONSES["default"], provider="mock",
                           model=self.model, prompt_tokens=50, completion_tokens=10)

    def health_check(self) -> bool:
        return True


# ── Shared fixtures ───────────────────────────────────────────────────────────

VULN_DIFF = """\
diff --git a/auth.py b/auth.py
index 000..111 100644
--- a/auth.py
+++ b/auth.py
@@ -1,3 +1,8 @@
+import hashlib
+
+# Hardcoded admin credentials
+ADMIN_PASSWORD = "super_secret_admin_123"
+
 def authenticate(user, pwd):
-    pass
+    hashed = hashlib.md5(pwd.encode()).hexdigest()
+    return hashed == hashlib.md5(ADMIN_PASSWORD.encode()).hexdigest()
"""

SECRET_DIFF = VULN_DIFF + '\napi_key = "sk-live-secret123456789abc"'


def _make_pipeline(cloud_consent=False, agents=None):
    cfg = NexarqConfig()
    cfg.privacy.cloud_consent = cloud_consent
    cfg.providers["default"] = ProviderConfig(name=ProviderName.OLLAMA, model="mock")
    cfg.default_agents = agents or ["security", "bugs", "review", "performance"]

    secrets = SecretsManager()
    factory = LLMFactory(cfg, secrets)
    mock_provider = MockLLMProvider(model="mock")

    return cfg, factory, mock_provider


# ── Scenario 1: Full pipeline with vulnerable code ────────────────────────────

class TestE2EFullPipeline:
    def test_pipeline_finds_security_issues(self):
        cfg, factory, provider = _make_pipeline(agents=["security"])
        orch = AgentOrchestrator(config=cfg, factory=factory, registry=REGISTRY)

        with patch.object(factory, "get_for_agent", return_value=provider):
            results = orch.run(VULN_DIFF, "python", ["security"])

        assert len(results) == 1
        r = results[0]
        assert r.agent_name == "security"
        assert r.success is True

    def test_pipeline_all_four_default_agents(self):
        cfg, factory, provider = _make_pipeline()
        orch = AgentOrchestrator(config=cfg, factory=factory, registry=REGISTRY)

        with patch.object(factory, "get_for_agent", return_value=provider):
            results = orch.run(VULN_DIFF, "python", cfg.default_agents)

        assert len(results) == 4
        names = {r.agent_name for r in results}
        assert names == {"security", "bugs", "review", "performance"}

    def test_all_results_are_successful(self):
        cfg, factory, provider = _make_pipeline()
        orch = AgentOrchestrator(config=cfg, factory=factory, registry=REGISTRY)

        with patch.object(factory, "get_for_agent", return_value=provider):
            results = orch.run(VULN_DIFF, "python", cfg.default_agents)

        for r in results:
            assert r.success is True, f"Agent {r.agent_name} failed: {r.error}"

    def test_results_have_latency(self):
        cfg, factory, provider = _make_pipeline(agents=["review"])
        orch = AgentOrchestrator(config=cfg, factory=factory, registry=REGISTRY)

        with patch.object(factory, "get_for_agent", return_value=provider):
            results = orch.run(VULN_DIFF, "python", ["review"])

        assert results[0].latency_ms >= 0

    def test_results_have_token_usage(self):
        cfg, factory, provider = _make_pipeline(agents=["security"])
        orch = AgentOrchestrator(config=cfg, factory=factory, registry=REGISTRY)

        with patch.object(factory, "get_for_agent", return_value=provider):
            results = orch.run(VULN_DIFF, "python", ["security"])

        assert results[0].token_usage.get("prompt", 0) > 0


# ── Scenario 2: Secret redaction before any agent sees the diff ───────────────

class TestE2ESecretRedaction:
    def test_secrets_never_reach_provider(self):
        cfg, factory, _ = _make_pipeline(agents=["security"])
        orch = AgentOrchestrator(config=cfg, factory=factory, registry=REGISTRY)

        seen_prompts = []

        class _CapturingProvider(MockLLMProvider):
            def _call_api(self, prompt, system=""):
                seen_prompts.append(prompt)
                return super()._call_api(prompt, system)

        with patch.object(factory, "get_for_agent", return_value=_CapturingProvider(model="mock")):
            orch.run(SECRET_DIFF, "python", ["security"])

        for prompt in seen_prompts:
            assert "sk-live-secret123456789abc" not in prompt, \
                "Raw secret reached the LLM provider — SEC-6 violation!"

    def test_redaction_result_logged(self):
        cfg, factory, provider = _make_pipeline(agents=["security"])
        audit = MagicMock(spec=AuditLogger)
        orch = AgentOrchestrator(config=cfg, factory=factory,
                                 registry=REGISTRY, audit=audit)

        with patch.object(factory, "get_for_agent", return_value=provider):
            orch.run(SECRET_DIFF, "python", ["security"])

        # Should have logged a diff_redaction event
        calls = [str(call) for call in audit.log_event.call_args_list]
        assert any("diff_redaction" in c for c in calls)


# ── Scenario 3: Diff engine → orchestrator integration ───────────────────────

class TestE2EDiffToOrchestrator:
    def test_diff_engine_feeds_orchestrator(self, tmp_path):
        diff_file = tmp_path / "test.patch"
        diff_file.write_text(VULN_DIFF)

        engine = DiffEngine()
        diff_result = engine.from_text(VULN_DIFF, "python")

        assert len(diff_result.files) == 1
        assert diff_result.primary_language == "python"

        cfg, factory, provider = _make_pipeline(agents=["security"])
        orch = AgentOrchestrator(config=cfg, factory=factory, registry=REGISTRY)

        with patch.object(factory, "get_for_agent", return_value=provider):
            results = orch.run(diff_result.combined_diff(), "python", ["security"])

        assert len(results) == 1

    def test_excluded_files_not_analysed(self):
        lock_diff = """\
diff --git a/package-lock.json b/package-lock.json
@@ -1,3 +1,5 @@
+  "version": "2.0.0",
+  "lockfileVersion": 2
"""
        engine = DiffEngine(exclude_patterns=["*.json"])
        result = engine.from_text(lock_diff)
        assert result.files == []


# ── Scenario 4: Full pipeline + interactive session ───────────────────────────

class TestE2EInteractiveSession:
    def test_session_answers_question_about_findings(self):
        cfg, factory, provider = _make_pipeline()
        orch = AgentOrchestrator(config=cfg, factory=factory, registry=REGISTRY)

        with patch.object(factory, "get_for_agent", return_value=provider):
            results = orch.run(VULN_DIFF, "python", ["security", "review"])

        # Start interactive session with those results
        session = InteractiveSession(results=results, diff=VULN_DIFF, provider=provider)
        session._ask("What is the most critical issue?")

        assert len(session._history) == 1
        assert len(session._history[0]["assistant"]) > 0

    def test_session_context_includes_agent_findings(self):
        cfg, factory, provider = _make_pipeline(agents=["security"])
        orch = AgentOrchestrator(config=cfg, factory=factory, registry=REGISTRY)

        with patch.object(factory, "get_for_agent", return_value=provider):
            results = orch.run(VULN_DIFF, "python", ["security"])

        session = InteractiveSession(results=results, diff=VULN_DIFF, provider=provider)
        # System prompt must reference the security findings
        assert "SECURITY" in session._system


# ── Scenario 5: Audit trail completeness ─────────────────────────────────────

class TestE2EAuditTrail:
    def test_all_agent_runs_logged(self, tmp_path):
        import json
        cfg, factory, provider = _make_pipeline()
        audit = AuditLogger(log_dir=tmp_path, enabled=True)
        orch = AgentOrchestrator(config=cfg, factory=factory,
                                 registry=REGISTRY, audit=audit)

        with patch.object(factory, "get_for_agent", return_value=provider):
            orch.run(VULN_DIFF, "python", ["security", "review"])

        log_file = list(tmp_path.glob("*.jsonl"))[0]
        entries = [json.loads(l) for l in log_file.read_text().splitlines() if l.strip()]
        agent_run_entries = [e for e in entries if e["event"] == "agent_run"]

        agent_names = {e["agent"] for e in agent_run_entries}
        assert "security" in agent_names
        assert "review" in agent_names

    def test_redaction_event_logged_when_secrets_present(self, tmp_path):
        import json
        cfg, factory, provider = _make_pipeline(agents=["security"])
        audit = AuditLogger(log_dir=tmp_path, enabled=True)
        orch = AgentOrchestrator(config=cfg, factory=factory,
                                 registry=REGISTRY, audit=audit)

        with patch.object(factory, "get_for_agent", return_value=provider):
            orch.run(SECRET_DIFF, "python", ["security"])

        log_file = list(tmp_path.glob("*.jsonl"))[0]
        entries = [json.loads(l) for l in log_file.read_text().splitlines() if l.strip()]
        events = [e["event"] for e in entries]
        assert "diff_redaction" in events


# ── Scenario 6: Formatter renders results without crashing ────────────────────

class TestE2EFormatting:
    def _null_console(self):
        import io
        return Console(file=io.StringIO(), force_terminal=False)

    def test_formatter_renders_full_pipeline_results(self):
        cfg, factory, provider = _make_pipeline()
        orch = AgentOrchestrator(config=cfg, factory=factory, registry=REGISTRY)

        with patch.object(factory, "get_for_agent", return_value=provider):
            results = orch.run(VULN_DIFF, "python", cfg.default_agents)

        formatter = ReportFormatter(console=self._null_console())
        formatter.print_header("abc123", "feat: add auth", 1)
        for r in results:
            formatter.print_result(r)
        formatter.print_summary(results)
        # No assertion needed — just must not raise
