"""Rich-based report formatter for agent results."""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from nexarq_cli.agents.base import AgentResult, Severity

# Severity → color, icon, rank
_SEV: dict[str, tuple[str, str, int]] = {
    # name: (color, label, sort_rank)
    "critical": ("bold red",      "CRIT", 0),
    "high":     ("red",           "HIGH", 1),
    "medium":   ("yellow",        " MED", 2),
    "low":      ("cyan",          " LOW", 3),
    "info":     ("bright_black",  "INFO", 4),
}

_AGENT_LABELS: dict[str, str] = {
    "security":        "Security",
    "secrets_detection": "Secrets",
    "bugs":            "Bugs",
    "concurrency":     "Concurrency",
    "memory_safety":   "Memory Safety",
    "resource_usage":  "Resource Usage",
    "performance":     "Performance",
    "review":          "Code Review",
    "code_smells":     "Code Smells",
    "style":           "Style",
    "refactor":        "Refactor",
    "maintainability": "Maintainability",
    "type_safety":     "Type Safety",
    "architecture":    "Architecture",
    "api_design":      "API Design",
    "database":        "Database",
    "dependency":      "Dependencies",
    "error_handling":  "Error Handling",
    "docstring":       "Docstrings",
    "test_coverage":   "Test Coverage",
    "logging_agent":   "Logging",
    "compliance":      "Compliance",
    "accessibility":   "Accessibility",
    "i18n":            "i18n",
    "standards":       "Standards",
    "devops":          "DevOps",
    "risk_scoring":    "Risk Score",
    "summary":         "Summary",
    "next_steps":      "Action Plan",
    "ai_fixes":        "AI Fixes",
    "explain":         "Explain",
}


def _sev(result: "AgentResult") -> tuple[str, str, int]:
    key = str(result.severity.value if hasattr(result.severity, "value") else result.severity)
    return _SEV.get(key, ("white", key[:4].upper(), 99))


def _label(name: str) -> str:
    return _AGENT_LABELS.get(name, name.replace("_", " ").title())


def _has_findings(result: "AgentResult") -> bool:
    return bool(result.output and len(result.output.strip()) > 30)


class ReportFormatter:
    """Formats agent results for terminal output using Rich."""

    def __init__(self, console: Console | None = None, verbose: bool = False) -> None:
        self._c = console or Console()
        self.verbose = verbose

    # ── Header ────────────────────────────────────────────────────────────────

    def print_header(
        self,
        commit_hash: str,
        commit_message: str,
        file_count: int,
        branch: str = "",
        author: str = "",
        change_type: str = "",
        languages: list[str] | None = None,
        framework: str = "auto",
    ) -> None:
        """Print a compact, one-panel review header."""
        meta_parts = []
        if branch:
            meta_parts.append(f"[dim]branch[/dim] [bold]{branch}[/bold]")
        if author:
            meta_parts.append(f"[dim]by[/dim] [bold]{author}[/bold]")
        if change_type:
            meta_parts.append(f"[dim]{change_type.replace('_', ' ')}[/dim]")
        if languages:
            meta_parts.append(f"[dim]{' · '.join(languages)}[/dim]")

        # Show which framework is orchestrating
        fw_label = {
            "langgraph": "LangGraph",
            "crewai":    "CrewAI",
            "thread":    "ThreadPool",
            "auto":      "auto",
        }.get(framework or "auto", framework or "auto")
        meta_parts.append(f"[dim]via[/dim] [dim cyan]{fw_label}[/dim cyan]")

        meta_line = "   ".join(meta_parts) if meta_parts else ""

        body = (
            f"[bold white]{commit_message[:80]}[/bold white]\n"
            f"[dim]{commit_hash}[/dim]   "
            f"[dim]{file_count} file{'s' if file_count != 1 else ''} changed[/dim]"
        )
        if meta_line:
            body += f"\n{meta_line}"

        self._c.print()
        self._c.print(
            Panel(
                body,
                title="[bold blue] NEXARQ  CODE  REVIEW [/bold blue]",
                border_style="blue",
                padding=(0, 2),
            )
        )

    # ── Live progress tick (called once per completed agent) ──────────────────

    def print_tick(self, result: "AgentResult") -> None:
        """Single-line status tick printed as each agent completes."""
        color, label, _ = _sev(result)
        agent = _label(result.agent_name)

        if result.error:
            status = "[red] ERR [/red]"
            note = f"[dim red]{result.error[:55]}[/dim red]"
        elif _has_findings(result):
            status = f"[{color}]{label}[/{color}]"
            first = result.output.strip().splitlines()[0][:50]
            note = f"[dim]{first}[/dim]"
        else:
            status = "[dim] --- [/dim]"
            note = "[dim]no findings[/dim]"

        ms = f"[dim]{result.latency_ms:.0f}ms[/dim]"
        self._c.print(f"  {status}  [bold]{agent:<20}[/bold]  {note}  {ms}")

    # ── Full result panel (printed after all agents finish) ───────────────────

    def print_result(self, result: "AgentResult") -> None:
        """Print a full result panel. Only called for agents that have findings."""
        if result.error:
            self._c.print(
                Panel(
                    f"[red]{result.error}[/red]",
                    title=f"[red]ERROR · {_label(result.agent_name).upper()}[/red]",
                    border_style="red",
                    padding=(0, 2),
                )
            )
            return

        if not _has_findings(result):
            return  # silent — already shown as a tick

        color, label, _ = _sev(result)
        border = color.replace("bold ", "")
        ms = f"[dim]{result.latency_ms:.0f}ms[/dim]"

        self._c.print(
            Panel(
                Markdown(result.output),
                title=f"[{color}]{label}[/{color}]  [bold]{_label(result.agent_name).upper()}[/bold]",
                subtitle=ms,
                border_style=border,
                padding=(1, 2),
            )
        )

        for w in result.warnings:
            self._c.print(f"  [yellow]![/yellow] {w}")

    # ── Summary table ─────────────────────────────────────────────────────────

    def print_summary(self, results: list["AgentResult"]) -> None:
        """Compact summary table sorted by severity."""
        if not results:
            return

        # Count findings
        findings = sum(1 for r in results if _has_findings(r) and r.success)
        errors = sum(1 for r in results if r.error)
        clean = sum(1 for r in results if r.success and not _has_findings(r))

        # Stat bar
        parts: list[str] = []
        if errors:
            parts.append(f"[red]{errors} error{'s' if errors != 1 else ''}[/red]")
        if findings:
            parts.append(f"[yellow]{findings} finding{'s' if findings != 1 else ''}[/yellow]")
        if clean:
            parts.append(f"[green]{clean} clean[/green]")
        self._c.print(f"\n  {'  |  '.join(parts)}  from {len(results)} agents\n")

        table = Table(
            box=box.SIMPLE_HEAD,
            show_header=True,
            header_style="bold dim",
            pad_edge=False,
            show_edge=False,
        )
        table.add_column("Agent",    style="bold",  min_width=18)
        table.add_column("Sev",      justify="center", min_width=6)
        table.add_column("Status",   justify="center", min_width=8)
        table.add_column("Tokens",   justify="right",  style="dim", min_width=7)
        table.add_column("Latency",  justify="right",  style="dim", min_width=7)

        sorted_results = sorted(results, key=lambda r: _sev(r)[2])

        for r in sorted_results:
            color, label, _ = _sev(r)
            if r.error:
                status_str = "[red]ERROR[/red]"
                sev_str = "[dim]-[/dim]"
            elif _has_findings(r):
                status_str = f"[{color}]FINDINGS[/{color}]"
                sev_str = f"[{color}]{label}[/{color}]"
            else:
                status_str = "[green]CLEAN[/green]"
                sev_str = "[dim]-[/dim]"

            tokens = str(sum(r.token_usage.values())) if r.token_usage else "-"
            latency = f"{r.latency_ms:.0f}ms"

            table.add_row(
                _label(r.agent_name),
                sev_str,
                status_str,
                tokens,
                latency,
            )

        self._c.print(table)

    # ── Misc helpers ──────────────────────────────────────────────────────────

    def print_rule(self, title: str = "") -> None:
        self._c.print(Rule(title, style="dim"))

    def print_error(self, message: str) -> None:
        self._c.print(f"\n[bold red]✗[/bold red] {message}")

    def print_success(self, message: str) -> None:
        self._c.print(f"[bold green]✓[/bold green] {message}")

    def print_info(self, message: str) -> None:
        self._c.print(f"[blue]·[/blue] {message}")

    def print_warning(self, message: str) -> None:
        self._c.print(f"[yellow]![/yellow] {message}")


def _severity_rank(severity) -> int:
    key = str(severity.value if hasattr(severity, "value") else severity)
    return _SEV.get(key, ("", "", 99))[2]
