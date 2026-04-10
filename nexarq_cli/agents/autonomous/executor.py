"""
Autonomous coding agent — powered by LangGraph.

Uses LangGraph's prebuilt create_react_agent which implements the
ReAct (Reason + Act + Observe) loop natively:

  Human message  →  [LLM decides tool]  →  [tool runs]  →  [LLM sees result]
                 ↑___________ loop until LLM stops calling tools ______________|

Architecture:
  - LLM:   ChatOllama / ChatOpenAI / ChatAnthropic  (via lc_llm bridge)
  - Tools: LangChain @tool decorated functions       (via lc_tools)
  - Graph: LangGraph create_react_agent              (the ReAct loop)

If LangGraph is not installed, falls back to the custom ReAct loop.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule

if TYPE_CHECKING:
    from nexarq_cli.config.schema import NexarqConfig

console = Console()

# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM = """\
You are Nexarq Coder — an autonomous coding assistant built on LangGraph.

Your job: complete the given task by reading files, writing code,
running tests, and documenting changes — step by step, explaining your
reasoning at every turn.

RULES:
1. Always read a file before modifying it — never guess its contents.
2. write_file requires the COMPLETE new file content, not a partial patch.
3. After modifying code, run the relevant tests if they exist.
4. One tool call at a time — do not batch multiple tools in one turn.
5. When the task is fully complete, summarise everything you did and stop.
6. The user must confirm every write_file and run_command — you don't
   need to ask; the tools handle it.
"""


_PLAN_PROMPT = """\
Task: {task}

Project ({file_count} tracked files):
{structure}

Git status: {git_status}

Produce a numbered step-by-step PLAN (markdown) — name each file you will
read, modify, create, or delete. Include test and doc steps where relevant.
"""


# ── Executor ───────────────────────────────────────────────────────────────────

class AutonomousAgent:
    """
    LangGraph-powered autonomous coding agent.

    Falls back to a custom ReAct loop when LangGraph / langchain-ollama
    are not installed.
    """

    def __init__(self, cfg: "NexarqConfig", repo_root: Path) -> None:
        self._cfg = cfg
        self._repo_root = repo_root

        # Set repo root for all tools
        from nexarq_cli.agents.autonomous.lc_tools import set_repo_root
        set_repo_root(repo_root)

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(self, task: str) -> None:
        console.print()
        console.print(Rule("[bold blue] Nexarq Coder  [LangGraph] [/bold blue]", style="blue"))
        console.print(f"\n  [dim]Task:[/dim] [bold white]{task}[/bold white]\n")

        try:
            self._run_langgraph(task)
        except ImportError as e:
            console.print(
                f"[yellow]LangGraph not installed ({e}).[/yellow]\n"
                "[dim]Falling back to built-in ReAct loop.\n"
                "Install with:  pip install 'nexarq-cli[langchain]'[/dim]\n"
            )
            self._run_fallback(task)

    # ── LangGraph path ─────────────────────────────────────────────────────────

    # Labels shown inline when each tool fires — Claude Code style
    _TOOL_META: dict[str, tuple[str, str]] = {
        "read_file":          ("Read",    "cyan"),
        "write_file":         ("Write",   "yellow"),
        "list_dir":           ("List",    "blue"),
        "find_files":         ("Find",    "blue"),
        "search_code":        ("Search",  "magenta"),
        "run_command":        ("Run",     "yellow"),
        "git_status":         ("Git",     "green"),
        "git_diff":           ("Diff",    "green"),
        "review_code":        ("Review",  "bold magenta"),
        "list_review_agents": ("Agents",  "dim"),
    }

    def _run_langgraph(self, task: str) -> None:
        from langgraph.prebuilt import create_react_agent
        from langchain_core.messages import HumanMessage, SystemMessage

        from nexarq_cli.frameworks.lc_llm import get_lc_llm
        from nexarq_cli.agents.autonomous.lc_tools import ALL_TOOLS

        llm = get_lc_llm(self._cfg)

        # ── Phase 1: Plan (streamed inline) ───────────────────────────────
        plan_text = self._generate_plan_lc(task, llm)
        if plan_text is None:
            return

        plan_section = _extract_plan(plan_text)
        console.print(
            Panel(
                Markdown(plan_section),
                title="[bold cyan] Plan  [LangGraph ReAct] [/bold cyan]",
                border_style="cyan",
                width=console.width,
            )
        )

        # ── Phase 2: Confirm ──────────────────────────────────────────────
        console.print("\n  Proceed? ([bold]y[/bold]/n/edit): ", end="")
        try:
            ans = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Aborted.[/yellow]")
            return
        if ans in ("n", "no"):
            console.print("[yellow]Aborted.[/yellow]")
            return
        if ans == "edit":
            console.print("  Revised task (Enter to keep original): ", end="")
            try:
                revised = input().strip()
                if revised:
                    task = revised
            except (EOFError, KeyboardInterrupt):
                pass

        # ── Phase 3: Execute — interactive, Claude Code style ─────────────
        console.print()
        console.print(Rule("[bold blue] Executing [/bold blue]", style="blue"))
        console.print()

        # `state_modifier` was removed in LangGraph ≥ 0.2.57; `prompt` replaces it.
        try:
            agent_executor = create_react_agent(
                llm, tools=ALL_TOOLS,
                prompt=SystemMessage(content=_SYSTEM),
            )
        except TypeError:
            agent_executor = create_react_agent(
                llm, tools=ALL_TOOLS,
                state_modifier=SystemMessage(content=_SYSTEM),
            )

        full_task = (
            f"{task}\n\n"
            f"Approved plan:\n{plan_section}\n\n"
            "Execute step by step. Call your first tool now."
        )
        inputs = {"messages": [HumanMessage(content=full_task)]}

        # Stream tokens + tool calls inline — Claude Code style:
        #   • LLM text tokens → printed as they arrive
        #   • Tool call header → shown when LLM announces the call (before it runs)
        #     Falls back to showing header from the ToolMessage if chunks missed it
        #   • write_file / run_command → show their own diff/confirm UI
        #   • Silent tools (read, search, …) → compact ↳ summary line after
        final_text = ""
        shown_tools: set[str] = set()   # tool_call_ids already announced
        pending_tool_name: str | None = None

        def _show_tool_header(name: str, args: dict | str) -> None:
            """Print the ⬡ Tool  filename label."""
            label, color = self._TOOL_META.get(name, ("Tool", "cyan"))
            if isinstance(args, dict):
                hint_val = next(iter(args.values()), "") if args else ""
            else:
                hint_val = _first_arg(str(args))
            hint = f" [dim]{str(hint_val)[:60]}[/dim]" if hint_val else ""
            console.print(f"\n  [{color}]⬡ {label}[/{color}]{hint}", highlight=False)

        try:
            for chunk, _meta in agent_executor.stream(inputs, stream_mode="messages"):
                kind = getattr(chunk, "type", "")

                # ── LLM text tokens ───────────────────────────────────────
                if kind == "ai":
                    text = chunk.content if isinstance(chunk.content, str) else ""
                    if text:
                        console.print(text, end="", markup=False)
                        final_text += text

                    # Approach 1: tool_calls (fully assembled — most reliable)
                    for tc in getattr(chunk, "tool_calls", None) or []:
                        name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
                        tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", "")
                        if name and tc_id not in shown_tools:
                            shown_tools.add(tc_id or name)
                            if final_text.strip():
                                console.print()
                            args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
                            _show_tool_header(name, args)
                            pending_tool_name = name
                            final_text = ""

                    # Approach 2: tool_call_chunks (streaming — fires earlier)
                    for tc in getattr(chunk, "tool_call_chunks", None) or []:
                        name = tc.get("name") or ""
                        tc_id = tc.get("id") or name
                        if name and tc_id not in shown_tools:
                            shown_tools.add(tc_id)
                            if final_text.strip():
                                console.print()
                            _show_tool_header(name, tc.get("args") or "")
                            pending_tool_name = name
                            final_text = ""

                # ── Tool result ───────────────────────────────────────────
                elif kind == "tool":
                    tool_name = getattr(chunk, "name", "") or pending_tool_name or ""
                    tc_id = getattr(chunk, "tool_call_id", "") or tool_name

                    # Fallback: header wasn't shown yet (tool_calls/chunks both missed)
                    if tc_id not in shown_tools and tool_name:
                        shown_tools.add(tc_id)
                        _show_tool_header(tool_name, "")

                    result = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                    is_silent = tool_name not in ("write_file", "run_command")
                    if is_silent and result.strip():
                        first = result.strip().splitlines()[0]
                        summary = first[:90] + ("…" if len(first) > 90 else "")
                        console.print(f"  [dim]↳ {summary}[/dim]")

                    pending_tool_name = None

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted.[/yellow]")
            return

        console.print()
        self._show_done(final_text)

    def _generate_plan_lc(self, task: str, llm) -> str | None:
        """Stream the planning LLM call inline, return full text."""
        from langchain_core.messages import HumanMessage

        structure = self._project_structure()
        git_status = self._run_git(["git", "status", "--short"]) or "Working tree clean."
        file_count = len(self._run_git(["git", "ls-files"]).splitlines())

        prompt = _PLAN_PROMPT.format(
            task=task, structure=structure,
            git_status=git_status, file_count=file_count,
        )

        console.print("  [dim]Planning…[/dim]\n")
        chunks: list[str] = []
        try:
            for token in llm.stream([HumanMessage(content=prompt)]):
                text = token.content if hasattr(token, "content") else str(token)
                if text:
                    console.print(text, end="", markup=False)
                    chunks.append(text)
            console.print("\n")
        except KeyboardInterrupt:
            console.print("\n[yellow]Planning interrupted.[/yellow]")
            return None

        return "".join(chunks).strip()

    # ── Fallback ReAct loop (no LangGraph) ────────────────────────────────────

    def _run_fallback(self, task: str) -> None:
        """Built-in ReAct loop used when LangGraph is not installed."""
        from nexarq_cli.agents.autonomous.tools import (
            describe_tools, call_tool, set_repo_root,
        )
        from nexarq_cli.llm.factory import LLMFactory
        from nexarq_cli.security.secrets import SecretsManager

        set_repo_root(self._repo_root)
        factory = LLMFactory(self._cfg, SecretsManager())
        provider = factory.get("default")

        structure = self._project_structure()
        git_status = self._run_git(["git", "status", "--short"]) or "Working tree clean."
        file_count = len(self._run_git(["git", "ls-files"]).splitlines())

        _FALLBACK_SYSTEM = (
            "You are an autonomous coding agent.\n"
            "Use EXACTLY this format for tool calls:\n"
            "Thought: <why>\nAction: <tool>\nparam: value\n\n"
            "To finish: DONE: <summary>\n\n"
            f"Tools:\n{describe_tools()}"
        )

        plan_prompt = _PLAN_PROMPT.format(
            task=task, structure=structure,
            git_status=git_status, file_count=file_count,
        )

        console.print("  [dim]Planning (fallback mode)…[/dim]\n")
        plan_chunks: list[str] = []
        try:
            for chunk in provider.stream(plan_prompt, system=_FALLBACK_SYSTEM):
                console.print(chunk, end="", markup=False)
                plan_chunks.append(chunk)
            console.print("\n")
        except KeyboardInterrupt:
            console.print("\n[yellow]Planning interrupted.[/yellow]")
            return

        plan_text = "".join(plan_chunks).strip()
        plan_section = _extract_plan(plan_text)

        console.print(
            Panel(
                Markdown(plan_section),
                title="[bold cyan] Plan  [built-in ReAct] [/bold cyan]",
                border_style="cyan",
                width=console.width,
            )
        )
        console.print("\n  Proceed? ([bold]y[/bold]/n): ", end="")
        try:
            ans = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if ans in ("n", "no"):
            return

        console.print()
        console.print(Rule("[bold blue] Executing [/bold blue]", style="blue"))

        messages = [
            {"role": "user", "content": f"Task: {task}\n\nPlan:\n{plan_section}\n\nExecute step by step."},
        ]

        import re
        MAX_STEPS = 30
        for step in range(1, MAX_STEPS + 1):
            console.print(f"\n  [dim]Step {step}[/dim]")
            chunks: list[str] = []
            prompt_str = "\n\n".join(
                f"{'User' if m['role']=='user' else 'Assistant'}:\n{m['content']}"
                for m in messages[-20:]
            )
            try:
                for chunk in provider.stream(prompt_str, system=_FALLBACK_SYSTEM):
                    console.print(chunk, end="", markup=False)
                    chunks.append(chunk)
                console.print()
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted.[/yellow]")
                break

            response = "".join(chunks).strip()
            messages.append({"role": "assistant", "content": response})

            done_match = re.search(r"DONE:\s*(.+)", response, re.DOTALL | re.IGNORECASE)
            if done_match:
                self._show_done(done_match.group(1).strip())
                return

            from nexarq_cli.agents.autonomous.executor import _parse_action
            action, params = _parse_action(response)
            if not action:
                messages.append({"role": "user", "content": "Use the tool format or output DONE."})
                continue

            console.print(f"\n  [bold cyan]→ {action}[/bold cyan]")
            observation = call_tool(action, params)
            messages.append({
                "role": "user",
                "content": f"Observation:\n{observation}\n\nContinue or output DONE.",
            })

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _show_done(self, summary: str) -> None:
        console.print()
        console.print(Rule("[bold green] Done [/bold green]", style="green"))
        console.print(
            Panel(
                Markdown(summary) if summary.strip() else "[dim]Task complete.[/dim]",
                title="[bold green]Summary[/bold green]",
                border_style="green",
                width=console.width,
            )
        )
        status = self._run_git(["git", "status", "--short"])
        if status and status != "Working tree clean.":
            console.print("\n[dim]Changed files:[/dim]")
            for line in status.splitlines():
                flag = line[:2].strip()
                path = line[3:]
                color = "green" if "A" in flag else "yellow" if "M" in flag else "red"
                console.print(f"  [{color}]{flag}[/{color}]  {path}")
        console.print()

    def _project_structure(self) -> str:
        raw = self._run_git(["git", "ls-files"])
        if not raw:
            return "(unavailable)"
        files = raw.splitlines()
        dirs: dict[str, list[str]] = {}
        for f in files:
            top = f.split("/")[0]
            dirs.setdefault(top, []).append(f)
        lines: list[str] = []
        for top, fs in sorted(dirs.items(), key=lambda x: -len(x[1])):
            sample = ", ".join(Path(f).name for f in fs[:3])
            more = f" +{len(fs)-3} more" if len(fs) > 3 else ""
            lines.append(f"  {top}/  ({len(fs)} files)  [{sample}{more}]")
        return "\n".join(lines[:25])

    def _run_git(self, cmd: list[str]) -> str:
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=10, cwd=str(self._repo_root),
            )
            return r.stdout.strip()
        except Exception:
            return ""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _first_arg(args_json: str) -> str:
    """Extract the first string value from a partial JSON args snippet for display."""
    import re
    m = re.search(r'["\']((?:[^"\'\\]|\\.){1,60})["\']', args_json or "")
    return m.group(1) if m else ""


def _extract_plan(response: str) -> str:
    """Pull the plan section out of the LLM response (everything before first tool call)."""
    import re
    # Stop at the first tool call pattern
    for marker in ("Action:", "```tool", "<tool_call>"):
        idx = response.find(marker)
        if idx > 0:
            return response[:idx].strip()
    return response.strip()


def _parse_action(text: str) -> tuple[str | None, dict]:
    """Parse the first Action block from a ReAct-format response."""
    lines = text.splitlines()
    action: str | None = None
    params: dict[str, str] = {}
    content_key: str | None = None
    content_buf: list[str] = []
    in_block = False

    for line in lines:
        stripped = line.strip()

        if stripped.lower().startswith("action:"):
            action = stripped[7:].strip().lower().replace(" ", "_").replace("-", "_")
            in_block = True
            content_key = None
            content_buf = []
            continue

        if not in_block:
            continue

        if content_key is not None:
            if stripped == "<END_CONTENT>":
                params[content_key] = "\n".join(content_buf)
                content_key = None
                content_buf = []
            else:
                content_buf.append(line)
            continue

        if stripped == "":
            continue

        if stripped.lower().startswith(("thought:", "done:")):
            break

        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip().lower().replace(" ", "_")
            val = val.strip()
            if val == "":
                content_key = key
            else:
                params[key] = val

    if content_key and content_buf:
        params[content_key] = "\n".join(content_buf)

    return action, params
