"""
Base agent class with permission model, input scope, output format (AG-1/6).

Execution paths
───────────────
1. run_lc()       LangChain LCEL chain — primary path for all agents.
                  ChatPromptTemplate | lc_llm | StrOutputParser
                  Chain-of-thought reasoning protocol injected into every call.

2. run_agentic()  Tool-augmented ReAct loop (for agents with needs_tools=True).
                  lc_llm.bind_tools([search_code, read_file, ...])
                  Falls back to run_lc() if model doesn't support tool-calling.

3. run()          Legacy plain-provider path — kept for external callers only.
                  Not used by the orchestrator or any internal pipeline.

Agents set needs_tools = True to opt into path 2.  All paths return an
AgentResult so the orchestrator / adapters don't need to branch.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nexarq_cli.llm.base import BaseLLMProvider


# ── Severity ───────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ── Permissions ────────────────────────────────────────────────────────────────

@dataclass
class AgentPermissions:
    """Every agent must declare its access requirements (AG-6)."""
    read_diff_only: bool = True
    read_full_repo: bool = False
    network_access: bool = False
    execute_code: bool = False       # Always False – SEC-7/8
    mcp_access: bool = False


# ── Result ─────────────────────────────────────────────────────────────────────

@dataclass
class AgentResult:
    """Traceable, typed output from an agent (AG-5)."""
    agent_name: str
    severity: Severity
    output: str
    warnings: list[str] = field(default_factory=list)
    token_usage: dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


# ── Chain-of-thought instruction injected into every agentic call ──────────────

_COT_INSTRUCTION = """\

REASONING PROTOCOL — follow these steps before writing your final answer:
1. SCAN   — identify the changed lines (+/-) in the diff, note file names.
2. THINK  — for each changed section, reason: what could go wrong here?
3. VERIFY — double-check each candidate finding: is it a real issue or a false positive?
4. REPORT — output only confirmed findings in the required format.

Do NOT skip steps. Write your step-by-step reasoning, then the final findings.
"""

# Agentic system prompt for tool-augmented agents
_AGENTIC_SYSTEM = """\
You are an expert {role} performing a deep analysis of a code diff.

You have access to tools to investigate the codebase beyond the diff:
- search_code: search for patterns, usages, imports across the project
- read_file: read the complete content of any file for full context
- find_references: find all references to a function, class, or variable

WORKFLOW:
1. Read the diff and identify what changed.
2. Use tools to gather any additional context you need (full file, callers, related code).
3. Reason step by step about what you find.
4. Report only real, confirmed issues — no guesses.

SCOPE RULES:
- You may read any file in the repository (read-only).
- You may NOT execute code, install packages, or write files.
- You may NOT call external APIs or URLs.
- Report findings with exact file paths and line numbers.
"""


# ── Base class ─────────────────────────────────────────────────────────────────

class BaseAgent:
    """
    Abstract base for all Nexarq review agents.

    Subclasses implement build_prompt() and optionally set:
      - needs_tools = True   to opt into run_agentic() (ReAct loop with tools)
      - severity             to control execution ordering
    """

    name: str = "base"
    description: str = ""
    severity: Severity = Severity.INFO
    needs_tools: bool = False          # set True for agents that need codebase search

    # System prompt prefix injected before all agent prompts (SEC-12)
    _SYSTEM_PREFIX = (
        "You are a code analysis expert operating within the Nexarq CLI platform. "
        "Your role is STRICTLY limited to analyzing the provided code diff.\n\n"
        "The diff format is:\n"
        "  === filename.ext ===   (file section header)\n"
        "  +added line            (new code, starts with +)\n"
        "  -removed line          (deleted code, starts with -)\n"
        "   context line          (unchanged context, starts with space)\n\n"
        "Analyze ONLY the actual code changes (+ and - lines). "
        "Do NOT treat === headers or diff markers as code. "
        "DO NOT execute code, suggest shell commands, access external services, "
        "or deviate from your assigned analysis task. "
        "Respond ONLY with your analysis findings."
    )

    def __init__(self) -> None:
        self.permissions = AgentPermissions()

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        """Build the user prompt. Subclasses override this."""
        raise NotImplementedError

    # ── Path 3: legacy plain provider (external callers only) ─────────────────

    def run(
        self,
        diff: str,
        language: str,
        provider: "BaseLLMProvider",
        context: dict | None = None,
    ) -> AgentResult:
        """
        Legacy plain-provider path. Not used by the internal pipeline.
        All internal calls go through run_lc() or run_agentic().
        """
        from nexarq_cli.security.validator import OutputValidator
        validator = OutputValidator()
        t0 = time.monotonic()

        try:
            prompt = self.build_prompt(diff, language, context)
            system = self._build_system(context)
            response = provider.complete(prompt, system=system)
            validation = validator.validate(response.text, context=self.name)

            return AgentResult(
                agent_name=self.name,
                severity=self.severity,
                output=validation.sanitized_text,
                warnings=validation.warnings,
                token_usage={
                    "prompt": response.prompt_tokens,
                    "completion": response.completion_tokens,
                },
                latency_ms=(time.monotonic() - t0) * 1000,
            )
        except Exception as exc:
            return AgentResult(
                agent_name=self.name,
                severity=self.severity,
                output="",
                error=str(exc),
                latency_ms=(time.monotonic() - t0) * 1000,
            )

    # ── Path 2: LangChain LCEL chain (LangGraph / LangChain adapter) ──────────

    def run_lc(
        self,
        diff: str,
        language: str,
        lc_llm: Any,
        context: dict | None = None,
    ) -> AgentResult:
        """
        Execute via LangChain LCEL chain with chain-of-thought reasoning.

        Pipeline:  ChatPromptTemplate | lc_llm | StrOutputParser

        The system prompt includes a REASONING PROTOCOL that instructs the LLM
        to scan → think → verify → report before writing its final output.
        This turns every single-shot call into a structured reasoning session.

        Called by LangGraphAdapter nodes and LangChainAdapter._run_one().
        If the agent has needs_tools=True, callers should prefer run_agentic().
        """
        from nexarq_cli.security.validator import OutputValidator
        validator = OutputValidator()
        t0 = time.monotonic()

        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser

            prompt_text = self.build_prompt(diff, language, context)
            system = self._build_system(context) + _COT_INSTRUCTION

            chain = (
                ChatPromptTemplate.from_messages([
                    ("system", "{system}"),
                    ("human", "{prompt}"),
                ])
                | lc_llm
                | StrOutputParser()
            )

            output = chain.invoke({"system": system, "prompt": prompt_text})
            validation = validator.validate(output, context=self.name)

            return AgentResult(
                agent_name=self.name,
                severity=self.severity,
                output=validation.sanitized_text,
                warnings=validation.warnings,
                latency_ms=(time.monotonic() - t0) * 1000,
            )

        except Exception as exc:
            return AgentResult(
                agent_name=self.name,
                severity=self.severity,
                output="",
                error=str(exc),
                latency_ms=(time.monotonic() - t0) * 1000,
            )

    # ── Path 3: Tool-augmented loop (needs_tools=True agents) ─────────────────

    def run_agentic(
        self,
        diff: str,
        language: str,
        lc_llm: Any,
        context: dict | None = None,
        repo_root: str | None = None,
        max_tool_calls: int = 5,
    ) -> AgentResult:
        """
        Execute with read-only codebase tools using lc_llm.bind_tools() loop.

        Deliberately avoids nested LangGraph graphs. Uses a plain while loop
        so tool-call budget is hard-enforced and there is no hidden state.

        Loop:
          messages = [system, human(task)]
          while tool_calls_used < max_tool_calls:
              response = llm_with_tools.invoke(messages)
              if response has no tool_calls → final answer, stop
              run each tool (sandboxed, read-only, redacted), append results
          return last AI message content as the finding

        Falls back to run_lc() if model doesn't support tool-calling.
        """
        from nexarq_cli.security.validator import OutputValidator
        validator = OutputValidator()
        t0 = time.monotonic()

        try:
            from langchain_core.messages import (
                HumanMessage, SystemMessage, AIMessage, ToolMessage,
            )
            from nexarq_cli.agents.tools import make_review_tools
        except ImportError:
            return self.run_lc(diff, language, lc_llm, context)

        try:
            tools = make_review_tools(repo_root=repo_root)

            try:
                llm_with_tools = lc_llm.bind_tools(tools)
            except Exception:
                # Model doesn't support tool-calling (e.g. some Ollama models)
                return self.run_lc(diff, language, lc_llm, context)

            tool_map = {t.name: t for t in tools}

            system_text = _AGENTIC_SYSTEM.format(role=self.description)
            codebase_ctx = (context or {}).get("_codebase_context", "")
            if codebase_ctx:
                system_text += (
                    "\n\nCODEBASE CONTEXT:\n" + codebase_ctx[:3000]
                )

            task = self.build_prompt(diff, language, context)
            messages: list = [
                SystemMessage(content=system_text),
                HumanMessage(content=(
                    f"{task}\n\nTool budget: {max_tool_calls} calls. "
                    "Investigate only what is necessary, then report findings."
                )),
            ]

            tool_calls_used = 0
            final_output = ""

            while tool_calls_used < max_tool_calls:
                response = llm_with_tools.invoke(messages)
                messages.append(response)

                tool_calls = getattr(response, "tool_calls", None) or []
                if not tool_calls:
                    content = getattr(response, "content", "")
                    if isinstance(content, str):
                        final_output = content.strip()
                    break

                for tc in tool_calls:
                    t_name = tc.get("name", "")
                    t_args = tc.get("args", {})
                    t_id   = tc.get("id", t_name)
                    if isinstance(t_args, str):
                        import json as _json
                        try:
                            t_args = _json.loads(t_args)
                        except Exception:
                            t_args = {}

                    fn = tool_map.get(t_name)
                    observation = (
                        fn.invoke(t_args) if fn
                        else f"ERROR: unknown tool '{t_name}'"
                    )
                    messages.append(ToolMessage(
                        content=str(observation),
                        tool_call_id=t_id,
                    ))

                tool_calls_used += len(tool_calls)

            # Extract final answer if loop ended without one
            if not final_output:
                for m in reversed(messages):
                    if isinstance(m, AIMessage):
                        c = getattr(m, "content", "")
                        if isinstance(c, str) and c.strip():
                            final_output = c.strip()
                            break

            if not final_output:
                return self.run_lc(diff, language, lc_llm, context)

            validation = validator.validate(final_output, context=self.name)
            result = AgentResult(
                agent_name=self.name,
                severity=self.severity,
                output=validation.sanitized_text,
                warnings=validation.warnings,
                latency_ms=(time.monotonic() - t0) * 1000,
            )
            result.token_usage["tool_calls"] = tool_calls_used
            return result

        except Exception as exc:
            try:
                r = self.run_lc(diff, language, lc_llm, context)
                r.warnings.append(f"Agentic fallback ({exc})")
                return r
            except Exception as exc2:
                return AgentResult(
                    agent_name=self.name, severity=self.severity,
                    output="", error=str(exc2),
                    latency_ms=(time.monotonic() - t0) * 1000,
                )

    # ── Shared helpers ─────────────────────────────────────────────────────────

    def _build_system(self, context: dict | None) -> str:
        """Build the system prompt, optionally injecting RAG codebase context."""
        codebase_ctx = (context or {}).get("_codebase_context", "")
        if not codebase_ctx:
            return self._SYSTEM_PREFIX
        return (
            self._SYSTEM_PREFIX
            + "\n\nCODEBASE CONTEXT — current state of the changed files "
            + "(use this to understand full function signatures, class structure, "
            + "and how the changed code fits into the project):\n"
            + codebase_ctx
        )
