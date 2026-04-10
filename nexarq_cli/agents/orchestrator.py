"""
Multi-agent orchestrator — flat parallel execution, security-first.

All selected agents run in a single parallel batch (ThreadPoolExecutor).
No tiers, no RAG injection, no deduplication overhead.

Security guarantees:
  - Diff redacted before any cloud call (SEC-6)
  - AgentPermissions enforced before every agent run (SEC-PERM)
  - Cloud consent checked per provider (PR-5/6)
  - Tool agents: path traversal protected, outputs redacted (SEC-PATH-1)
  - All runs logged to audit trail (SEC-16)

Cost governance:
  - AgentSelector picks the minimal relevant agent set from diff context
  - max_agents hard cap (default 12) prevents runaway costs
  - Tool-call budget enforced per agentic agent
  - Result cache (SHA256, 24 h TTL) avoids re-paying for the same diff
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterator

from nexarq_cli.agents.base import AgentResult, Severity
from nexarq_cli.agents.registry import REGISTRY, AgentRegistry
from nexarq_cli.agents.selector import AgentSelector
from nexarq_cli.config.schema import NexarqConfig
from nexarq_cli.llm.factory import LLMFactory
from nexarq_cli.reporting.audit import AuditLogger
from nexarq_cli.security.redaction import Redactor


# ── Permission enforcement ────────────────────────────────────────────────────

def _check_permissions(agent, config: NexarqConfig) -> str | None:
    """
    Return an error string if the agent is not allowed to run, else None.
    Enforces AgentPermissions declared on every agent (SEC-PERM).
    """
    perms = agent.permissions
    agent_cfg = config.effective_agent_config(agent.name)
    cfg_perms = agent_cfg.permissions

    # Cloud consent for non-local providers
    provider_cfg = config.effective_provider(agent.name)
    provider_name = str(
        provider_cfg.name.value if hasattr(provider_cfg.name, "value")
        else provider_cfg.name
    )
    if provider_name != "ollama" and not config.privacy.cloud_consent:
        return (
            "Cloud provider blocked: cloud_consent is False. "
            "Run: nexarq config set cloud_consent true"
        )

    # Full repo access: downgrade silently if config disallows
    if perms.read_full_repo and not cfg_perms.read_full_repo:
        agent.permissions.read_full_repo = False

    # Code execution is always blocked (SEC-7/8)
    if perms.execute_code:
        return f"Agent '{agent.name}' declared execute_code=True — blocked by policy."

    # Network access requires explicit config opt-in
    if perms.network_access and not cfg_perms.network_access:
        return f"Agent '{agent.name}' requires network_access but config disallows it."

    return None


# ── Repo root helper ──────────────────────────────────────────────────────────

def _resolve_repo_root() -> str:
    gd = os.environ.get("GIT_DIR")
    if gd:
        p = Path(gd)
        return str((p.parent if p.name == ".git" else p).resolve())
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return str(Path.cwd())


# ── Result cache ──────────────────────────────────────────────────────────────

class _ResultCache:
    """
    File-based cache keyed by SHA256(diff + agent_name + model).
    Prevents re-paying LLM costs for the same diff reviewed twice
    (e.g. amend + re-push, or re-running nexarq run manually).
    TTL: 24 hours.
    """
    _TTL_SECONDS = 86_400  # 24 h

    def __init__(self) -> None:
        self._dir = Path("~/.nexarq/cache").expanduser()
        self._dir.mkdir(parents=True, exist_ok=True)

    def _key(self, diff: str, agent_name: str, model: str) -> str:
        raw = f"{diff[:4000]}|{agent_name}|{model}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, diff: str, agent_name: str, model: str) -> AgentResult | None:
        import time
        path = self._dir / f"{self._key(diff, agent_name, model)}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            if time.time() - data.get("ts", 0) > self._TTL_SECONDS:
                path.unlink(missing_ok=True)
                return None
            return AgentResult(
                agent_name=data["agent_name"],
                severity=Severity(data["severity"]),
                output=data["output"],
                warnings=data.get("warnings", []),
                token_usage=data.get("token_usage", {}),
                latency_ms=data.get("latency_ms", 0.0),
            )
        except Exception:
            return None

    def put(self, result: AgentResult, diff: str, model: str) -> None:
        import time
        path = self._dir / f"{self._key(diff, result.agent_name, model)}.json"
        try:
            sev = result.severity.value if hasattr(result.severity, "value") else str(result.severity)
            path.write_text(json.dumps({
                "ts": time.time(),
                "agent_name": result.agent_name,
                "severity": sev,
                "output": result.output,
                "warnings": result.warnings,
                "token_usage": result.token_usage,
                "latency_ms": result.latency_ms,
            }))
        except Exception:
            pass


# ── Orchestrator ──────────────────────────────────────────────────────────────

class AgentOrchestrator:
    """
    Flat parallel multi-agent orchestrator.

    All agents selected for a diff run in a single ThreadPoolExecutor batch.
    Results are yielded as they complete (fastest agents surface first).
    """

    def __init__(
        self,
        config: NexarqConfig,
        factory: LLMFactory,
        registry: AgentRegistry = REGISTRY,
        audit: AuditLogger | None = None,
        max_agents: int = 12,
    ) -> None:
        self._config = config
        self._factory = factory
        self._registry = registry
        self._audit = audit
        self._max_agents = max_agents
        self._redactor = Redactor(config.privacy.redact_patterns)
        self._cache = _ResultCache()

    # ── Public API ────────────────────────────────────────────────────────────

    def run(
        self,
        diff: str,
        language: str,
        agent_names: list[str] | None = None,
        context: dict | None = None,
        diff_result=None,
    ) -> list[AgentResult]:
        return list(self.stream(diff, language, agent_names, context, diff_result))

    def stream(
        self,
        diff: str,
        language: str,
        agent_names: list[str] | None = None,
        context: dict | None = None,
        diff_result=None,
        # kept for call-site compat — unused
        max_workers: int = 0,
        framework: str = "",
    ) -> Iterator[AgentResult]:

        # ── 1. Redact diff before any processing ─────────────────────────────
        from nexarq_cli.utils.diff_cleaner import clean_diff
        cleaned = clean_diff(diff)
        redacted = self._redactor.redact(cleaned)
        if redacted.redacted_count > 0 and self._audit:
            self._audit.log_event("diff_redaction", {
                "count": redacted.redacted_count,
                "patterns": redacted.patterns_matched,
            })
        safe_diff = redacted.text

        # ── 2. Build minimal shared context ──────────────────────────────────
        ctx: dict = dict(context or {})
        if diff_result is not None:
            ctx.update({
                "_diff_context":  diff_result.context_summary(),
                "_change_type":   diff_result.change_type,
                "_branch":        diff_result.branch,
                "_languages":     diff_result.all_languages,
                "_changed_files": "\n".join(f"  - {f}" for f in (diff_result.files or [])),
            })

        # ── 3. Select agents from diff context ────────────────────────────────
        if agent_names:
            names = agent_names
        elif diff_result is not None:
            selector = AgentSelector(self._registry, self._config)
            priority, parallel = selector.select(diff_result)
            # Flat list: priority agents first so fastest-to-finish surfaces sooner
            names = list(dict.fromkeys(priority + parallel))
        else:
            # No diff_result → run all enabled agents
            names = self._registry.names()

        # ── 4. Cap agent count ────────────────────────────────────────────────
        names = names[: self._max_agents]

        # ── 5. Resolve tool budget from config ────────────────────────────────
        try:
            tool_budget = self._config.execution.tool_call_budget
        except Exception:
            tool_budget = 5

        # ── 6. Model key for cache ────────────────────────────────────────────
        try:
            default_prov = self._config.providers.get("default") or next(
                iter(self._config.providers.values())
            )
            model_key = str(default_prov.model or "unknown")
        except Exception:
            model_key = "unknown"

        # ── 7. Init LangChain LLM once — shared across all threads ───────────
        from nexarq_cli.frameworks.lc_llm import get_lc_llm
        lc_llm = get_lc_llm(self._config)

        # ── 8. Repo root for agentic tool calls ───────────────────────────────
        repo_root = ctx.get("_repo_root") or _resolve_repo_root()

        # ── 9. Run all agents in one flat parallel batch ──────────────────────
        yield from self._run_batch(
            names, safe_diff, language, ctx,
            repo_root, tool_budget, model_key, lc_llm,
        )

    # ── Batch runner ──────────────────────────────────────────────────────────

    def _run_batch(
        self,
        names: list[str],
        diff: str,
        language: str,
        context: dict | None,
        repo_root: str,
        tool_budget: int,
        model_key: str,
        lc_llm,
    ) -> Iterator[AgentResult]:
        if not names:
            return

        def _run_one(name: str) -> AgentResult:
            try:
                agent = self._registry.get(name)

                # SEC-PERM: enforce permissions before anything else
                perm_error = _check_permissions(agent, self._config)
                if perm_error:
                    return AgentResult(
                        agent_name=name, severity=agent.severity,
                        output="", error=perm_error,
                    )

                provider_cfg = self._config.effective_provider(name)
                provider_name = str(
                    provider_cfg.name.value if hasattr(provider_cfg.name, "value")
                    else provider_cfg.name
                )

                # Cache lookup
                cached = self._cache.get(diff, name, model_key)
                if cached is not None:
                    if self._audit:
                        self._audit.log_event("cache_hit", {"agent": name})
                    return cached

                if lc_llm is None:
                    return AgentResult(
                        agent_name=name, severity=agent.severity,
                        output="", error="LangChain LLM not initialised — check provider config.",
                    )

                # run_agentic() gives the agent codebase search tools and
                # falls back to run_lc() automatically for models that don't
                # support tool-calling (e.g. some Ollama variants).
                result: AgentResult = agent.run_agentic(
                    diff, language, lc_llm, context,
                    repo_root=repo_root,
                    max_tool_calls=tool_budget,
                )

                # Cache successful non-empty results
                if result.success and result.output:
                    self._cache.put(result, diff, model_key)

                if self._audit:
                    self._audit.log_agent_run(name, result, provider_name)

                return result

            except Exception as exc:
                return AgentResult(
                    agent_name=name, severity=Severity.INFO,
                    output="", error=str(exc),
                )

        workers = min(max(len(names), 1), 20)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_run_one, n): n for n in names}
            try:
                for future in as_completed(futures):
                    yield future.result()
            except (KeyboardInterrupt, SystemExit):
                for f in futures:
                    f.cancel()
                raise
