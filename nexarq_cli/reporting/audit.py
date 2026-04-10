"""Audit logger – SEC-16/17/18: log all agent actions and API calls."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nexarq_cli.agents.base import AgentResult

LOG_DIR = Path(os.environ.get("NEXARQ_LOG_DIR", "~/.nexarq/logs")).expanduser()


class AuditLogger:
    """
    Append-only structured audit log for all Nexarq operations.

    SEC-16: Log all agent actions
    SEC-17: Log all external API calls
    SEC-18: Provide audit trail
    """

    def __init__(
        self,
        log_dir: Path = LOG_DIR,
        enabled: bool = True,
        log_level: str = "INFO",
    ) -> None:
        self.enabled = enabled
        self._log_dir = log_dir
        self._logger: logging.Logger | None = None

        if enabled:
            self._setup_logger(log_level)

    # ── public ───────────────────────────────────────────────────────────────

    def log_agent_run(self, agent_name: str, result: "AgentResult", provider: str) -> None:
        """Log an agent execution event (SEC-16)."""
        self._write({
            "event": "agent_run",
            "agent": agent_name,
            "provider": provider,
            "success": result.success,
            "severity": str(result.severity.value if hasattr(result.severity, "value") else result.severity),
            "tokens": result.token_usage,
            "latency_ms": round(result.latency_ms, 1),
            "warnings": result.warnings,
            "error": result.error,
        })

    def log_api_call(self, provider: str, model: str, tokens: dict, success: bool) -> None:
        """Log an outbound LLM API call (SEC-17)."""
        self._write({
            "event": "api_call",
            "provider": provider,
            "model": model,
            "tokens": tokens,
            "success": success,
        })

    def log_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Generic structured log entry."""
        self._write({"event": event_type, **data})

    def log_hook(self, hook_type: str, commit: str, agents_run: list[str]) -> None:
        """Log a Git hook trigger."""
        self._write({
            "event": "hook_trigger",
            "hook": hook_type,
            "commit": commit,
            "agents": agents_run,
        })

    # ── internal ─────────────────────────────────────────────────────────────

    def _write(self, data: dict) -> None:
        if not self.enabled or self._logger is None:
            return
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self._logger.info(json.dumps(entry))

    def _setup_logger(self, log_level: str) -> None:
        self._log_dir.mkdir(parents=True, exist_ok=True)
        log_file = self._log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"

        # Use a unique logger name per instance to prevent handler cross-contamination
        # across tests that use different tmp_path directories.
        unique_name = f"nexarq.audit.{id(self)}"
        self._logger = logging.getLogger(unique_name)
        self._logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        self._logger.propagate = False

        if not self._logger.handlers:
            handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=50 * 1024 * 1024,  # 50 MB
                backupCount=7,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)


# Lazy import to avoid circular
import logging.handlers  # noqa: E402
