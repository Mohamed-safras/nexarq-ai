"""
LangChain adapter (SRS 3.13).

Uses LangChain's chain abstraction to wrap Nexarq agents as LangChain tools,
enabling integration with LangChain memory, tracing (LangSmith), and callbacks.

Install: pip install langchain langchain-core
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Iterator

from nexarq_cli.agents.base import AgentResult, Severity
from nexarq_cli.frameworks.base import FrameworkAdapter


def _resolve_repo_root() -> str | None:
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


class LangChainAdapter(FrameworkAdapter):
    """
    Wraps Nexarq agents as LangChain LCEL chains.

    Each agent becomes a ChatPromptTemplate | LLM | StrOutputParser chain
    when lc_llm is available, enabling LangSmith tracing and callbacks.
    Falls back to provider.complete() if LangChain is not installed.
    """

    framework_name = "langchain"

    def _check_import(self) -> None:
        import langchain  # noqa: F401

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(
        self,
        diff: str,
        language: str,
        agent_names: list[str] | None = None,
        context: dict | None = None,
        diff_result=None,
    ) -> list[AgentResult]:
        """Execute agents via LangChain LCEL chains and return all results."""
        return list(self.stream(diff, language, agent_names, context, diff_result))

    def stream(
        self,
        diff: str,
        language: str,
        agent_names: list[str] | None = None,
        context: dict | None = None,
        diff_result=None,
    ) -> Iterator[AgentResult]:
        """Stream results as each agent completes."""
        ctx = dict(context or {})
        names = self._resolve_names(agent_names, diff_result)

        # Inject codebase context (RAG)
        if "_codebase_context" not in ctx and diff_result is not None:
            try:
                from nexarq_cli.rag.retriever import ContextRetriever
                codebase_ctx = ContextRetriever().retrieve(diff_result)
                if codebase_ctx:
                    ctx["_codebase_context"] = codebase_ctx
            except Exception:
                pass

        # Build LangChain LLM once — shared across all agents
        lc_llm = None
        try:
            from nexarq_cli.frameworks.lc_llm import get_lc_llm
            lc_llm = get_lc_llm(self._config)
        except Exception:
            pass

        repo_root = ctx.get("_repo_root") or _resolve_repo_root()

        for name in names:
            yield self._run_one(name, diff, language, ctx, lc_llm, repo_root)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _run_one(
        self,
        name: str,
        diff: str,
        language: str,
        context: dict,
        lc_llm=None,
        repo_root: str | None = None,
    ) -> AgentResult:
        try:
            agent = self._registry.get(name)

            # Enforce cloud consent
            pcfg = self._config.effective_provider(name)
            pname = str(pcfg.name.value if hasattr(pcfg.name, "value") else pcfg.name)
            if pname != "ollama" and not self._config.privacy.cloud_consent:
                return AgentResult(
                    agent_name=name,
                    severity=agent.severity,
                    output="",
                    error="Cloud provider blocked — cloud_consent is False",
                )

            if lc_llm is not None and getattr(agent, "needs_tools", False):
                # Path 3: tool-augmented ReAct loop
                return agent.run_agentic(diff, language, lc_llm, context, repo_root=repo_root)
            elif lc_llm is not None:
                # Path 2: LangChain LCEL chain with CoT reasoning
                return agent.run_lc(diff, language, lc_llm, context)
            else:
                # Path 1: fallback plain provider.complete()
                provider = self._factory.get_for_agent(name)
                return agent.run(diff, language, provider, context)

        except Exception as exc:
            return AgentResult(
                agent_name=name,
                severity=Severity.INFO,
                output="",
                error=str(exc),
            )

    def _resolve_names(self, agent_names: list[str] | None, diff_result) -> list[str]:
        from nexarq_cli.agents.selector import AgentSelector
        selector = AgentSelector(self._registry, self._config)
        if agent_names:
            return selector._filter_enabled(agent_names)
        if diff_result is not None:
            priority, parallel = selector.select(diff_result, None)
            return priority + parallel
        defaults = self._config.default_agents or list(self._registry.names())
        return selector._filter_enabled(defaults)

    def as_tools(self, diff: str, language: str) -> list[Any]:
        """
        Return Nexarq agents as LangChain StructuredTools for use in
        custom LangChain pipelines (e.g. LangGraph nodes, AgentExecutor).
        """
        try:
            from langchain.tools import StructuredTool
        except ImportError as e:
            raise RuntimeError("LangChain not installed.") from e

        tools = []
        for name in self._registry.names():
            agent = self._registry.get(name)
            provider = self._factory.get_for_agent(name)
            tool = StructuredTool.from_function(
                func=lambda d=diff, la=language, a=agent, p=provider: a.run(d, la, p),
                name=f"nexarq_{name}",
                description=agent.description,
            )
            tools.append(tool)
        return tools
