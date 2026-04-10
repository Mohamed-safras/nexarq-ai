"""
LangGraph adapter — review pipeline as a stateful directed graph.

Architecture:
  ┌──────────────────────────────────────────────────────────────────┐
  │  START                                                           │
  │    │                                                             │
  │    ▼  (sequential — highest severity first)                      │
  │  [security] → [secrets_detection] → [bugs] → [concurrency]      │
  │    │                                                             │
  │    ▼  (parallel fan-out via Send API)                            │
  │  [review] [performance] [type_safety] [error_handling] …         │
  │    │                                                             │
  │    ▼  (sequential — always last)                                 │
  │  [risk_scoring] → [summary] → [next_steps]                       │
  │    │                                                             │
  │  END                                                             │
  └──────────────────────────────────────────────────────────────────┘

Each node runs one Nexarq agent and appends its AgentResult to state.

Install:  pip install 'nexarq-cli[langchain]'
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Annotated, Any, Iterator, TypedDict

from nexarq_cli.agents.base import AgentResult, Severity
from nexarq_cli.frameworks.base import FrameworkAdapter

# Agents that must run before all others (security-critical)
_PRIORITY_AGENTS = ["security", "secrets_detection", "bugs", "concurrency"]


def _resolve_repo_root() -> str | None:
    """Auto-detect repository root for tool-augmented agents."""
    import os
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

# Agents that always run last, in this order
_FINAL_AGENTS = ["risk_scoring", "summary", "next_steps"]


# ── Graph state ────────────────────────────────────────────────────────────────

def _merge_results(a: list[AgentResult], b: list[AgentResult]) -> list[AgentResult]:
    """Reducer for the results field — merges parallel branch results."""
    return a + b


class ReviewState(TypedDict):
    diff: str
    language: str
    context: dict
    results: Annotated[list[AgentResult], _merge_results]


# ── Adapter ────────────────────────────────────────────────────────────────────

class LangGraphAdapter(FrameworkAdapter):
    """
    Run the Nexarq review pipeline as a LangGraph StateGraph.

    Each review agent is a graph node.  Priority agents run sequentially,
    remaining agents fan-out in parallel via LangGraph's Send API, then
    risk_scoring / summary / next_steps run sequentially at the end.
    """

    framework_name = "langgraph"

    def _check_import(self) -> None:
        import langgraph  # noqa: F401

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(
        self,
        diff: str,
        language: str,
        agent_names: list[str] | None = None,
        context: dict | None = None,
        diff_result=None,
    ) -> list[AgentResult]:
        """Execute the review pipeline and return all results."""
        return list(self.stream(diff, language, agent_names, context, diff_result=diff_result))

    def stream(
        self,
        diff: str,
        language: str,
        agent_names: list[str] | None = None,
        context: dict | None = None,
        diff_result=None,
    ) -> Iterator[AgentResult]:
        """Stream results as each LangGraph node completes."""
        try:
            from langgraph.graph import StateGraph, START, END
        except ImportError as e:
            raise ImportError(
                "LangGraph not installed.\n"
                "Run: pip install 'nexarq-cli[langchain]'  or  pip install langgraph"
            ) from e

        names = self._resolve_names(agent_names, diff_result)
        ctx = dict(context or {})

        # Inject codebase context (RAG)
        if "_codebase_context" not in ctx and diff_result is not None:
            try:
                from nexarq_cli.rag.retriever import ContextRetriever
                codebase_ctx = ContextRetriever().retrieve(diff_result)
                if codebase_ctx:
                    ctx["_codebase_context"] = codebase_ctx
            except Exception:
                pass

        # Build the LangChain LLM once — shared by all nodes so every agent
        # runs through a proper LCEL chain (ChatPromptTemplate | LLM | Parser).
        lc_llm = None
        try:
            from nexarq_cli.frameworks.lc_llm import get_lc_llm
            lc_llm = get_lc_llm(self._config)
        except Exception:
            pass  # fall back to plain provider.complete() inside each node

        # Resolve repo root for tool-augmented agents
        repo_root = ctx.get("_repo_root") or _resolve_repo_root()

        graph = self._build_graph(names, diff, language, ctx, lc_llm, repo_root)

        initial: ReviewState = {
            "diff": diff,
            "language": language,
            "context": ctx,
            "results": [],
        }

        seen: set[str] = set()
        for event in graph.stream(initial, stream_mode="updates"):
            for node_name, state_update in event.items():
                if node_name in ("__start__", "__end__"):
                    continue
                for result in state_update.get("results", []):
                    if result.agent_name not in seen:
                        seen.add(result.agent_name)
                        yield result

    # ── Graph construction ─────────────────────────────────────────────────────

    def _build_graph(
        self,
        names: list[str],
        diff: str,
        language: str,
        context: dict,
        lc_llm=None,
        repo_root: str | None = None,
    ) -> Any:
        from langgraph.graph import StateGraph, START, END

        priority = [n for n in _PRIORITY_AGENTS if n in names]
        final    = [n for n in _FINAL_AGENTS    if n in names]
        parallel = [n for n in names if n not in priority and n not in final]

        builder = StateGraph(ReviewState)

        # ── Priority nodes (sequential) ──────────────────────────────────
        for name in priority:
            builder.add_node(name, self._make_node(name, lc_llm, repo_root))

        # ── Parallel nodes (fan-out) ─────────────────────────────────────
        for name in parallel:
            builder.add_node(name, self._make_node(name, lc_llm, repo_root))

        # ── Final nodes (sequential) ─────────────────────────────────────
        for name in final:
            builder.add_node(name, self._make_node(name, lc_llm, repo_root))

        # ── Edges ────────────────────────────────────────────────────────
        all_ordered = priority + parallel + final
        if not all_ordered:
            builder.add_edge(START, END)
            return builder.compile()

        builder.add_edge(START, all_ordered[0])

        # Chain priority nodes sequentially
        for i in range(len(priority) - 1):
            builder.add_edge(priority[i], priority[i + 1])

        # After priority → fan out to all parallel nodes simultaneously
        last_priority = priority[-1] if priority else None
        parallel_entry = parallel[0] if parallel else None
        final_entry    = final[0]    if final    else None

        if last_priority:
            if parallel:
                # All parallel nodes start right after the last priority node
                for p in parallel:
                    builder.add_edge(last_priority, p)
            elif final_entry:
                builder.add_edge(last_priority, final_entry)
            else:
                builder.add_edge(last_priority, END)
        elif parallel_entry:
            builder.add_edge(START, parallel_entry)

        if parallel:
            # All parallel nodes converge into the first final node (or END)
            target = final_entry or END
            for p in parallel:
                builder.add_edge(p, target)

        # Chain final nodes sequentially
        for i in range(len(final) - 1):
            builder.add_edge(final[i], final[i + 1])

        if final:
            builder.add_edge(final[-1], END)
        elif not parallel and not priority:
            builder.add_edge(START, END)

        return builder.compile()

    def _make_node(self, name: str, lc_llm=None, repo_root: str | None = None):
        """
        Return a LangGraph node function for a Nexarq agent.

        Dispatch order:
          1. run_agentic()  — if agent.needs_tools=True and lc_llm available
                              Agent gets read_file, search_code, find_references tools
                              and runs a full ReAct loop before producing findings.
          2. run_lc()       — if lc_llm available (LCEL chain with CoT reasoning)
          3. run()          — fallback via plain provider.complete()
        """
        registry   = self._registry
        factory    = self._factory
        config     = self._config
        _lc_llm    = lc_llm
        _repo_root = repo_root

        def node_fn(state: ReviewState) -> dict:
            try:
                agent = registry.get(name)

                # Enforce cloud consent
                pcfg  = config.effective_provider(name)
                pname = str(pcfg.name.value if hasattr(pcfg.name, "value") else pcfg.name)
                if pname != "ollama" and not config.privacy.cloud_consent:
                    result = AgentResult(
                        agent_name=name, severity=agent.severity, output="",
                        error="Cloud provider blocked — cloud_consent is False",
                    )
                elif _lc_llm is not None and getattr(agent, "needs_tools", False):
                    # ── Path 3: tool-augmented ReAct loop ─────────────────
                    result = agent.run_agentic(
                        state["diff"], state["language"],
                        _lc_llm, state["context"],
                        repo_root=_repo_root,
                    )
                elif _lc_llm is not None:
                    # ── Path 2: LangChain LCEL chain with CoT ─────────────
                    result = agent.run_lc(
                        state["diff"], state["language"], _lc_llm, state["context"]
                    )
                else:
                    # ── Path 1: plain provider.complete() ─────────────────
                    provider = factory.get_for_agent(name)
                    result = agent.run(
                        state["diff"], state["language"], provider, state["context"]
                    )
            except Exception as exc:
                result = AgentResult(
                    agent_name=name, severity=Severity.INFO, output="", error=str(exc)
                )
            return {"results": [result]}

        node_fn.__name__ = name
        return node_fn

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _resolve_names(self, agent_names: list[str] | None, diff_result) -> list[str]:
        """Determine which agents to run, respecting config and diff context."""
        if agent_names:
            return self._selector._filter_enabled(agent_names)
        if diff_result is not None:
            priority, parallel = self._selector.select(diff_result, None)
            return priority + parallel
        defaults = self._config.default_agents or list(self._registry.names())
        return self._selector._filter_enabled(defaults)

    @property
    def _selector(self):
        from nexarq_cli.agents.selector import AgentSelector
        return AgentSelector(self._registry, self._config)
