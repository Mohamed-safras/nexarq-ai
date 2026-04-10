"""
Scenarios: ReportFormatter rendering, AuditLogger structured output,
           severity ordering, token display, audit file creation.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from rich.console import Console

from nexarq_cli.agents.base import AgentResult, Severity
from nexarq_cli.reporting.audit import AuditLogger
from nexarq_cli.reporting.formatter import ReportFormatter, _severity_rank


def _result(name="security", severity=Severity.CRITICAL, output="Found SQL injection.",
            error=None, latency=120.5, tokens=None):
    return AgentResult(
        agent_name=name,
        severity=severity,
        output=output,
        error=error,
        latency_ms=latency,
        token_usage=tokens or {"prompt": 100, "completion": 200},
    )


# ── ReportFormatter ───────────────────────────────────────────────────────────

class TestReportFormatter:
    def _formatter(self):
        console = Console(file=open("/dev/null" if Path("/dev/null").exists() else "NUL", "w"),
                          force_terminal=False)
        return ReportFormatter(console=console)

    def test_print_result_success(self):
        f = self._formatter()
        f.print_result(_result())   # should not raise

    def test_print_result_with_error(self):
        f = self._formatter()
        f.print_result(_result(error="Timeout after 120s"))  # should not raise

    def test_print_summary_no_crash(self):
        f = self._formatter()
        results = [
            _result("security", Severity.CRITICAL),
            _result("bugs", Severity.HIGH),
            _result("review", Severity.MEDIUM),
        ]
        f.print_summary(results)

    def test_print_header_no_crash(self):
        f = self._formatter()
        f.print_header("abc123", "feat: add new feature", 5)

    def test_severity_rank_ordering(self):
        assert _severity_rank(Severity.CRITICAL) < _severity_rank(Severity.HIGH)
        assert _severity_rank(Severity.HIGH) < _severity_rank(Severity.MEDIUM)
        assert _severity_rank(Severity.MEDIUM) < _severity_rank(Severity.LOW)
        assert _severity_rank(Severity.LOW) < _severity_rank(Severity.INFO)

    def test_summary_sorted_by_severity(self):
        """Summary table should show critical before info."""
        results = [
            _result("explain", Severity.INFO),
            _result("security", Severity.CRITICAL),
            _result("review", Severity.MEDIUM),
        ]
        # Sort manually and verify order matches severity rank
        sorted_results = sorted(results, key=lambda r: _severity_rank(r.severity))
        assert sorted_results[0].agent_name == "security"
        assert sorted_results[-1].agent_name == "explain"


# ── AuditLogger ───────────────────────────────────────────────────────────────

class TestAuditLogger:
    def test_disabled_logger_writes_nothing(self, tmp_path):
        audit = AuditLogger(log_dir=tmp_path, enabled=False)
        audit.log_event("test", {"key": "value"})
        log_files = list(tmp_path.glob("*.jsonl"))
        assert log_files == []

    def test_enabled_logger_creates_log_file(self, tmp_path):
        audit = AuditLogger(log_dir=tmp_path, enabled=True)
        audit.log_event("startup", {"version": "0.1.0"})
        log_files = list(tmp_path.glob("*.jsonl"))
        assert len(log_files) == 1

    def test_log_event_writes_valid_json(self, tmp_path):
        audit = AuditLogger(log_dir=tmp_path, enabled=True)
        audit.log_event("test_event", {"agent": "security", "count": 3})
        log_file = list(tmp_path.glob("*.jsonl"))[0]
        line = log_file.read_text(encoding="utf-8").strip()
        data = json.loads(line)
        assert data["event"] == "test_event"
        assert data["agent"] == "security"
        assert "ts" in data

    def test_log_agent_run_writes_entry(self, tmp_path):
        audit = AuditLogger(log_dir=tmp_path, enabled=True)
        result = _result("security", Severity.CRITICAL, output="SQL injection found")
        audit.log_agent_run("security", result, provider="ollama")
        log_file = list(tmp_path.glob("*.jsonl"))[0]
        data = json.loads(log_file.read_text(encoding="utf-8").strip())
        assert data["event"] == "agent_run"
        assert data["agent"] == "security"
        assert data["provider"] == "ollama"
        assert data["success"] is True

    def test_log_agent_run_failed_agent(self, tmp_path):
        audit = AuditLogger(log_dir=tmp_path, enabled=True)
        result = _result("bugs", error="Timeout")
        audit.log_agent_run("bugs", result, provider="ollama")
        log_file = list(tmp_path.glob("*.jsonl"))[0]
        data = json.loads(log_file.read_text(encoding="utf-8").strip())
        assert data["success"] is False
        assert data["error"] == "Timeout"

    def test_log_hook_writes_entry(self, tmp_path):
        audit = AuditLogger(log_dir=tmp_path, enabled=True)
        audit.log_hook("post-commit", "abc123", ["security", "bugs"])
        log_file = list(tmp_path.glob("*.jsonl"))[0]
        data = json.loads(log_file.read_text(encoding="utf-8").strip())
        assert data["event"] == "hook_trigger"
        assert data["hook"] == "post-commit"
        assert "security" in data["agents"]

    def test_log_api_call_writes_entry(self, tmp_path):
        audit = AuditLogger(log_dir=tmp_path, enabled=True)
        audit.log_api_call("ollama", "codellama",
                           {"prompt": 100, "completion": 200}, success=True)
        log_file = list(tmp_path.glob("*.jsonl"))[0]
        data = json.loads(log_file.read_text(encoding="utf-8").strip())
        assert data["event"] == "api_call"
        assert data["provider"] == "ollama"

    def test_multiple_events_appended(self, tmp_path):
        audit = AuditLogger(log_dir=tmp_path, enabled=True)
        audit.log_event("event1", {})
        audit.log_event("event2", {})
        log_file = list(tmp_path.glob("*.jsonl"))[0]
        lines = [l for l in log_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 2

    def test_log_dir_created_automatically(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c"
        audit = AuditLogger(log_dir=deep, enabled=True)
        audit.log_event("test", {})
        assert deep.exists()
