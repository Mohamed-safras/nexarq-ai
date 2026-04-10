"""Interactive terminal chat session after review completes."""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markdown import Markdown
from rich.panel import Panel

from nexarq_cli.utils.console import console

if TYPE_CHECKING:
    from nexarq_cli.agents.base import AgentResult
    from nexarq_cli.llm.base import BaseLLMProvider


_BANNER = """[bold blue]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold blue]
  [bold white]Nexarq Chat[/bold white]  [dim]— ask anything about the review[/dim]

  [dim]Type a question, or use a command:[/dim]
  [cyan]/findings[/cyan]  list all findings         [cyan]/agents[/cyan]   who ran
  [cyan]/agent[/cyan]    [dim]<task>[/dim] — autonomous coding   [cyan]/clear[/cyan]    clear screen
  [cyan]/history[/cyan]  conversation log           [cyan]/exit[/cyan]     quit
[bold blue]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold blue]
"""

_SYSTEM = """\
You are Nexarq, a code review assistant. You have just completed an automated
multi-agent review of a code diff. The review results are provided below.

Your job is to help the developer understand and act on the findings.
Answer questions clearly and concisely. When suggesting fixes, show code.
Do NOT invent issues that are not in the review results.

--- REVIEW RESULTS ---
{results}
--- END OF REVIEW ---

The original code diff is also available for reference:
--- DIFF ---
{diff}
--- END DIFF ---
"""


class InteractiveSession:
    """
    Post-review interactive chat loop.
    The user can ask follow-up questions about review findings.
    """

    def __init__(
        self,
        results: list["AgentResult"],
        diff: str,
        provider: "BaseLLMProvider",
    ) -> None:
        self._results = results
        self._diff = diff
        self._provider = provider
        self._history: list[dict[str, str]] = []
        self._system = self._build_system()

    # ── public ───────────────────────────────────────────────────────────────

    def start(self) -> None:
        console.print(_BANNER)

        while True:
            try:
                # Use plain input() — more reliable than Prompt.ask() in CMD
                # windows opened via `cmd /c start` (no ANSI prompt support).
                console.print("[bold cyan]nexarq>[/bold cyan] ", end="")
                user_input = input().strip()
            except EOFError:
                # stdin closed (e.g. piped input exhausted or terminal gone)
                console.print("\n[dim]Session ended.[/dim]")
                break
            except KeyboardInterrupt:
                # Ctrl+C at the prompt → clean exit (not an error)
                console.print("\n[dim]Exiting. Type /exit next time to quit.[/dim]")
                break

            if not user_input:
                continue

            # ── built-in commands ─────────────────────────────────────────
            if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
                console.print("[dim]Goodbye.[/dim]")
                break

            if user_input.lower() == "/clear":
                console.clear()
                console.print(_BANNER)
                continue

            if user_input.lower() == "/agents":
                self._print_agents()
                continue

            if user_input.lower() == "/findings":
                self._print_findings()
                continue

            if user_input.lower() == "/history":
                self._print_history()
                continue

            if user_input.lower().startswith("/agent"):
                agent_task = user_input[6:].strip()
                self._run_agent(agent_task)
                continue

            # ── LLM query ─────────────────────────────────────────────────
            self._ask(user_input)

    # ── internal ─────────────────────────────────────────────────────────────

    def _ask(self, question: str) -> None:
        # Build prompt with conversation history
        history_text = ""
        if self._history:
            lines = []
            for turn in self._history[-6:]:
                lines.append(f"User: {turn['user']}")
                lines.append(f"Assistant: {turn['assistant']}")
            history_text = "\n".join(lines) + "\n\n"

        prompt = f"{history_text}User: {question}\nAssistant:"

        # Stream the response token-by-token
        # Ctrl+C during streaming cancels THIS response but stays in the loop.
        console.print()
        chunks: list[str] = []
        try:
            for chunk in self._provider.stream(prompt, system=self._system):
                console.print(chunk, end="", markup=False)
                chunks.append(chunk)
            console.print("\n")  # blank line after stream ends
        except KeyboardInterrupt:
            console.print("\n[dim](interrupted)[/dim]\n")
            return  # back to prompt, not exit
        except Exception as exc:
            console.print(f"\n[red]Error:[/red] {exc}\n")
            return

        answer = "".join(chunks).strip()
        if answer:
            self._history.append({"user": question, "assistant": answer})

    def _build_system(self) -> str:
        results_text = self._format_results()
        diff_preview = self._diff[:3000] + "\n...(truncated)" if len(self._diff) > 3000 else self._diff
        return _SYSTEM.format(results=results_text, diff=diff_preview)

    def _format_results(self) -> str:
        lines = []
        for r in self._results:
            sev = str(r.severity.value if hasattr(r.severity, "value") else r.severity)
            lines.append(f"[{sev.upper()}] {r.agent_name.upper()}")
            if r.error:
                lines.append(f"  ERROR: {r.error}")
            elif r.output:
                lines.append(r.output[:2000])
            else:
                lines.append("  No findings.")
            lines.append("")
        return "\n".join(lines)

    def _print_agents(self) -> None:
        from rich.table import Table
        from rich import box as _box
        t = Table(box=_box.SIMPLE_HEAD, show_header=True, header_style="bold dim",
                  pad_edge=False, show_edge=False)
        t.add_column("Agent",   min_width=20)
        t.add_column("Sev",     justify="center", min_width=6)
        t.add_column("Status",  justify="center")
        t.add_column("Latency", justify="right", style="dim")
        for r in self._results:
            sev = str(r.severity.value if hasattr(r.severity, "value") else r.severity)
            color = {"critical":"bold red","high":"red","medium":"yellow",
                     "low":"cyan","info":"bright_black"}.get(sev,"white")
            status = "[green]clean[/green]" if r.success and not r.output.strip() else \
                     "[red]error[/red]" if r.error else f"[{color}]findings[/{color}]"
            t.add_row(r.agent_name.replace("_"," "), f"[{color}]{sev[:4].upper()}[/{color}]",
                      status, f"{r.latency_ms:.0f}ms")
        console.print()
        console.print(t)
        console.print()

    def _print_findings(self) -> None:
        console.print()
        _SEV_ORDER = {"critical":0,"high":1,"medium":2,"low":3,"info":4}
        sorted_r = sorted(self._results, key=lambda r: _SEV_ORDER.get(
            str(r.severity.value if hasattr(r.severity,"value") else r.severity), 99))
        for r in sorted_r:
            sev = str(r.severity.value if hasattr(r.severity,"value") else r.severity)
            color = {"critical":"bold red","high":"red","medium":"yellow",
                     "low":"cyan","info":"bright_black"}.get(sev,"white")
            if r.error:
                console.print(f"  [red]ERR[/red]  [bold]{r.agent_name}[/bold]  [dim red]{r.error[:70]}[/dim red]")
            elif not r.output or len(r.output.strip()) < 20:
                console.print(f"  [dim] ·   {r.agent_name:<20} no findings[/dim]")
            else:
                first = r.output.strip().splitlines()[0][:72]
                console.print(f"  [{color}]{sev[:4].upper()}[/{color}]  [bold]{r.agent_name:<20}[/bold]  [dim]{first}[/dim]")
        console.print()

    def _print_history(self) -> None:
        if not self._history:
            console.print("[dim]No conversation history yet.[/dim]")
            return
        for i, turn in enumerate(self._history, 1):
            console.print(f"[bold cyan]{i}. You:[/bold cyan] {turn['user']}")
            console.print(f"   [dim]{turn['assistant'][:100]}...[/dim]\n")

    def _run_agent(self, task: str) -> None:
        """Launch the autonomous agent from inside the chat session."""
        if not task:
            console.print(
                "  [dim]Usage:[/dim] [cyan]/agent[/cyan] [dim]<task description>[/dim]\n"
                "  [dim]Example:[/dim] /agent add error handling to the auth module\n"
            )
            return

        import os, subprocess
        from pathlib import Path

        # Detect repo root
        git_dir = os.environ.get("GIT_DIR")
        if git_dir:
            p = Path(git_dir)
            repo_root = (p.parent if p.name == ".git" else p).resolve()
        else:
            try:
                r = subprocess.run(
                    ["git", "rev-parse", "--show-toplevel"],
                    capture_output=True, text=True, timeout=5,
                )
                repo_root = Path(r.stdout.strip()).resolve() if r.returncode == 0 else Path.cwd()
            except Exception:
                repo_root = Path.cwd()

        try:
            from nexarq_cli.agents.autonomous.executor import AutonomousAgent
            from nexarq_cli.config.manager import ConfigManager
            cfg = ConfigManager().load()
            runner = AutonomousAgent(cfg=cfg, repo_root=repo_root)
            runner.run(task)
        except KeyboardInterrupt:
            console.print("\n[yellow]Agent interrupted.[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Agent error:[/red] {e}")
