"""nexarq run – execute the review pipeline."""
from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from nexarq_cli.agents.orchestrator import AgentOrchestrator
from nexarq_cli.agents.registry import REGISTRY
from nexarq_cli.config.manager import ConfigManager
from nexarq_cli.git.diff import DiffEngine
from nexarq_cli.llm.factory import LLMFactory
from nexarq_cli.reporting.audit import AuditLogger
from nexarq_cli.reporting.formatter import ReportFormatter, _severity_rank
from nexarq_cli.reporting.token_tracker import TokenTracker
from nexarq_cli.security.secrets import SecretsManager
from nexarq_cli.utils.console import console

app = typer.Typer()

# Pattern to extract file path + code block pairs from agent output
_FIX_FILE_RE = re.compile(r"[Ff]ile:\s*`?(.+?)`?\s*\n", re.MULTILINE)
_CODE_BLOCK_RE = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)
_AFTER_BLOCK_RE = re.compile(
    r"[Aa]fter[:\s]*```(?:\w+)?\n(.*?)```",
    re.DOTALL,
)


@app.command()
def run(
    agents: Optional[str] = typer.Option(
        None, "--agents", "-a",
        help="Comma-separated agent names (default: auto-select from diff)",
    ),
    language: Optional[str] = typer.Option(
        None, "--language", "-l",
        help="Language hint (auto-detected if omitted)",
    ),
    diff_file: Optional[Path] = typer.Option(
        None, "--diff", "-d",
        help="Read diff from file instead of Git",
    ),
    profile: str = typer.Option("default", "--profile", "-p", help="Config profile"),
    hook: Optional[str] = typer.Option(
        None, "--hook", hidden=True,
        help="Hook type (post-commit, pre-push) – set by git hooks",
    ),
    framework: Optional[str] = typer.Option(
        None, "--framework", "-f",
        help="Orchestration framework: auto (default), langgraph, crewai, autogen, langchain, thread",
    ),
    mode: Optional[str] = typer.Option(
        None, "--mode", "-m",
        help=(
            "Execution tier: fast (3 agents, cheapest), smart (diff-selected, default), "
            "deep (all + tools), auto (smart + escalate on CRITICAL)"
        ),
    ),
    list_agents: bool = typer.Option(False, "--list-agents", help="List available agents"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    no_summary: bool = typer.Option(False, "--no-summary", help="Skip summary table"),
    interactive: bool = typer.Option(
        True, "--interactive/--no-interactive", "-i",
        help="Interactive approval flow after review (default: on)",
    ),
) -> None:
    """Run the multi-agent code review pipeline."""

    if list_agents:
        _print_agents()
        return

    # Install shutdown handlers — when the terminal window is closed, or the
    # parent process dies, kill this process immediately without waiting for
    # any blocking Ollama HTTP calls in background threads.
    _install_shutdown_handler()

    # ── Auto-setup on first run ───────────────────────────────────────────
    mgr = ConfigManager(profile=profile)
    from nexarq_cli.cli.setup_wizard import is_configured, run_auto_setup
    if not is_configured(mgr.config_path):
        from nexarq_cli.git.diff import DiffEngine as _DE
        repo_root = None
        try:
            import subprocess as _sp, os as _os
            gd = _os.environ.get("GIT_DIR")
            if gd:
                from pathlib import Path as _P
                _gp = _P(gd)
                repo_root = (_gp.parent if _gp.name == ".git" else _gp).resolve()
            else:
                _r = _sp.run(["git","rev-parse","--show-toplevel"],
                              capture_output=True, text=True, timeout=5)
                if _r.returncode == 0:
                    repo_root = _P(_r.stdout.strip()).resolve()
        except Exception:
            pass

        if not run_auto_setup(mgr.config_path, repo_root):
            return   # user cancelled setup
        mgr.reset_cache()  # reload fresh config from disk

    cfg = mgr.load()

    if not getattr(cfg, "enabled", True):
        console.print(
            "[yellow]Nexarq is disabled.[/yellow] "
            "Run [bold]nexarq enable[/bold] to re-enable."
        )
        return

    # Apply --mode CLI override to execution tier config
    _VALID_MODES = ("fast", "smart", "deep", "auto")
    if mode:
        m = mode.lower().strip()
        if m not in _VALID_MODES:
            console.print(
                f"[yellow]Unknown mode '{m}'. Valid: {', '.join(_VALID_MODES)}. "
                "Using config default.[/yellow]"
            )
        else:
            cfg.execution.mode = m  # type: ignore[assignment]
    elif hook:
        # No explicit --mode passed and we're running from a git hook:
        # use hook_mode (defaults to "fast") so commits feel instant.
        cfg.execution.mode = cfg.execution.hook_mode  # type: ignore[assignment]

    formatter = ReportFormatter(verbose=verbose)
    secrets = SecretsManager()
    factory = LLMFactory(cfg, secrets)

    audit = AuditLogger(
        log_dir=cfg.audit.log_dir,
        enabled=cfg.audit.enabled,
        log_level=cfg.audit.log_level,
    )

    context: dict = {}
    standards_file = mgr.home / "standards.md"
    if standards_file.exists():
        context["standards"] = standards_file.read_text(encoding="utf-8")

    # ── Get diff ──────────────────────────────────────────────────────────
    engine = DiffEngine(
        exclude_patterns=cfg.git.exclude_patterns,
        max_diff_lines=cfg.git.max_diff_lines,
    )

    try:
        if diff_file:
            diff_text = diff_file.read_text(encoding="utf-8")
            diff_result = engine.from_text(diff_text, language or "unknown")
        elif hook == "pre-push":
            diff_result = engine.staged()
        else:
            diff_result = engine.last_commit()
    except Exception as exc:
        formatter.print_error(f"Could not extract diff: {exc}")
        raise typer.Exit(1)

    if not diff_result.files:
        formatter.print_info("No reviewable changes found.")
        return

    lang = language or diff_result.primary_language
    agent_names = [a.strip() for a in agents.split(",")] if agents else None

    # ── Resolve framework early (needed for header) ───────────────────────
    _VALID_FRAMEWORKS = ("auto", "langgraph", "crewai", "autogen", "langchain", "thread")
    fw = (framework or "auto").lower().strip()
    if fw not in _VALID_FRAMEWORKS:
        formatter.print_warning(
            f"Unknown framework '{fw}'. Using 'auto'. "
            f"Valid: {', '.join(_VALID_FRAMEWORKS)}"
        )
        fw = "auto"

    # ── Header ────────────────────────────────────────────────────────────
    formatter.print_header(
        diff_result.commit_hash,
        diff_result.commit_message,
        len(diff_result.files),
        branch=diff_result.branch,
        author=diff_result.author,
        change_type=diff_result.change_type,
        languages=diff_result.all_languages,
        framework=fw,
    )

    # ── Orchestrate ───────────────────────────────────────────────────────
    orchestrator = AgentOrchestrator(
        config=cfg,
        factory=factory,
        registry=REGISTRY,
        audit=audit,
    )

    all_results = []
    combined = diff_result.combined_diff(cfg.git.max_diff_lines)

    provider_name = cfg.providers.get(
        "default", cfg.providers.get(list(cfg.providers)[0])
    ).name
    budget = cfg.token_budget.max_tokens_per_run if cfg.token_budget.enabled else 0
    token_tracker = TokenTracker(
        provider=str(provider_name),
        budget_tokens=budget,
        cost_rates=cfg.token_budget.cost_rates if cfg.token_budget.enabled else None,
    )

    # ── Phase 1: stream agents with live spinner ──────────────────────────
    console.print()
    try:
        from rich.status import Status

        status = Status(
            "  [dim]Running agents…[/dim]",
            console=console,
            spinner="dots",
            spinner_style="bold blue",
        )
        status.start()

        for result in orchestrator.stream(combined, lang, agent_names, context, diff_result=diff_result):
            if result.agent_name == "next_steps":
                continue

            # Stop spinner → print completed tick → restart for next agent
            status.stop()
            formatter.print_tick(result)
            token_tracker.record(result)
            all_results.append(result)

            if token_tracker.is_over_budget():
                formatter.print_warning(
                    f"Token budget exceeded ({budget} tokens). Stopping."
                )
                break

            next_label = result.agent_name.replace("_", " ").title()
            status.update(f"  [dim]Running:[/dim] [bold cyan]{next_label}[/bold cyan]")
            status.start()

        status.stop()

    except ImportError as exc:
        from nexarq_cli.utils.autodeps import resolve as _resolve
        _resolve(exc)  # installs package + re-execs process — never returns
        raise typer.Exit(1)  # unreachable, satisfies type checker

    # ── Phase 2: print full findings sorted by severity ───────────────────
    findings = [r for r in sorted(all_results, key=lambda r: _severity_rank(r.severity))
                if (r.success and r.output and len(r.output.strip()) > 30) or r.error]
    if findings:
        console.print()
        formatter.print_rule("Findings")
        console.print()
        for result in findings:
            formatter.print_result(result)

    # ── Summary ───────────────────────────────────────────────────────────
    if not no_summary and all_results:
        formatter.print_summary(all_results)

    # ── What to do next — only when there are real code findings ─────────────
    from nexarq_cli.utils.diff_cleaner import is_code_diff
    has_code = is_code_diff(set(diff_result.all_languages))
    real_findings = [
        r for r in all_results
        if r.success and r.output and len(r.output.strip()) > 30
    ]

    next_steps_result = None
    if has_code and real_findings:
        next_steps_result = _run_next_steps(
            all_results=real_findings,
            diff=combined,
            lang=lang,
            context=context,
            orchestrator=orchestrator,
            diff_result=diff_result,
        )

    if all_results:
        usage = token_tracker.summary()
        console.print(f"\n[dim]Token usage: {usage}[/dim]")

    if hook:
        audit.log_hook(hook, diff_result.commit_hash, [r.agent_name for r in all_results])

    # Combine all results including next_steps for the interactive session
    all_results_full = all_results + ([next_steps_result] if next_steps_result else [])

    # ── Approval flow — only when there are fixable code findings ────────────
    # For doc-only or no-findings commits, go straight to chat (or exit)
    has_fixable = any(
        r.success and r.output and len(r.output.strip()) > 30
        for r in all_results
    ) and has_code

    if hook == "post-commit" and interactive and all_results:
        _reopen_stdin()
        if has_fixable:
            _run_approval_flow(
                all_results=all_results,
                diff=combined,
                lang=lang,
                context=context,
                orchestrator=orchestrator,
                diff_result=diff_result,
            )
        from nexarq_cli.cli.interactive import InteractiveSession
        provider = factory.get("default")
        InteractiveSession(all_results_full, combined, provider).start()
        # After chat ends: give a moment before the window closes
        _wait_to_close()
        return

    # ── Chat mode (manual nexarq run) ────────────────────────────────────
    if interactive and all_results and not hook:
        from nexarq_cli.cli.interactive import InteractiveSession
        provider = factory.get("default")
        InteractiveSession(all_results_full, combined, provider).start()

    # Exit code for pre-push blocking
    critical_failures = [r for r in all_results if not r.success and r.error]
    if critical_failures and hook == "pre-push":
        raise typer.Exit(1)


# ── Next steps synthesis ──────────────────────────────────────────────────────

def _run_next_steps(
    all_results,
    diff: str,
    lang: str,
    context: dict,
    orchestrator,
    diff_result,
):
    """
    Run the next_steps agent with full context of all other agent findings.

    Only runs when real code findings exist (>30 chars of output).
    Returns the AgentResult, or None if skipped/failed.
    """
    from nexarq_cli.agents.registry import REGISTRY
    if "next_steps" not in REGISTRY.names():
        return None

    # Only pass agents that produced meaningful findings
    meaningful = [r for r in all_results if r.success and len(r.output.strip()) > 30]
    if not meaningful:
        return None

    # Build compact findings summary
    lines: list[str] = []
    for r in meaningful:
        sev = str(r.severity.value if hasattr(r.severity, "value") else r.severity)
        lines.append(f"\n[{sev.upper()}] {r.agent_name.upper()}")
        lines.append(r.output[:1500])

    agent_results_text = "\n".join(lines)

    next_context = dict(context)
    next_context["_agent_results"] = agent_results_text
    if diff_result:
        next_context["_changed_files"] = "\n".join(
            f"  - {f}" for f in (diff_result.files or [])
        )

    from rich.rule import Rule
    console.print()
    console.print(Rule("[bold blue]What to do next[/bold blue]", style="blue"))
    console.print()

    try:
        results = list(
            orchestrator.stream(diff, lang, ["next_steps"], next_context, diff_result=diff_result)
        )
        if results and results[0].success and results[0].output.strip():
            result = results[0]
            from rich.panel import Panel
            from rich.markdown import Markdown
            # Cap width to avoid edge-to-edge spanning
            panel_width = min(100, (getattr(console, "width", 104) or 104) - 4)
            console.print(
                Panel(
                    Markdown(result.output),
                    title="[bold green]ACTION PLAN[/bold green]",
                    border_style="green",
                    padding=(1, 2),
                    width=panel_width,
                )
            )
            return result
        elif results and results[0].error:
            console.print(f"[dim]Could not generate action plan: {results[0].error}[/dim]")
    except Exception as exc:
        console.print(f"[dim]Action plan skipped: {exc}[/dim]")

    return None


# ── Approval flow ─────────────────────────────────────────────────────────────

def _run_approval_flow(
    all_results,
    diff: str,
    lang: str,
    context: dict,
    orchestrator: AgentOrchestrator,
    diff_result,
) -> None:
    """
    After the review, offer to generate and apply AI fixes.

    Each fix is shown with a diff preview and requires explicit y/n/q approval.
    Nothing is ever applied automatically.
    """
    from rich.rule import Rule as _Rule
    successful = [r for r in all_results if r.success and len(r.output.strip()) > 30]
    if not successful:
        return  # nothing to fix, go straight to chat

    console.print()
    console.print(_Rule(style="dim"))
    console.print(
        f"\n  [bold]{len(successful)}[/bold] agent(s) found issues. "
        "[dim]Generate AI fix suggestions?[/dim]"
    )

    # Ask whether to generate AI fixes
    console.print(
        "  [bold]Apply AI fixes?[/bold] "
        "[dim](y = yes / n = skip / q = quit)[/dim] ",
        end="",
    )
    try:
        choice = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print("\n[yellow]Skipped.[/yellow]")
        return

    if choice == "q":
        console.print("[yellow]Quit — no fixes applied.[/yellow]")
        return

    if choice != "y":
        console.print("[dim]Skipped fix generation.[/dim]")
        _show_manual_hint()
        return

    # ── Run ai_fixes agent ────────────────────────────────────────────────
    console.print("\n[bold blue]Generating AI fixes…[/bold blue]\n")

    fix_results = list(
        orchestrator.stream(diff, lang, ["ai_fixes"], context, diff_result=diff_result)
    )

    if not fix_results or not fix_results[0].success:
        err = fix_results[0].error if fix_results else "no output"
        console.print(f"[red]AI fix generation failed:[/red] {err}")
        _show_manual_hint()
        return

    fix_output = fix_results[0].output
    fixes = _extract_fixes(fix_output, diff_result)

    if not fixes:
        console.print("[yellow]No structured fixes found in AI output.[/yellow]")
        console.print(fix_output)
        _show_manual_hint()
        return

    console.print(f"\n[bold]Found [cyan]{len(fixes)}[/cyan] proposed fix(es).[/bold]\n")

    applied = 0
    for idx, (file_path, new_code, description) in enumerate(fixes, 1):
        from rich.panel import Panel
        from rich.syntax import Syntax

        console.print(f"[bold]Fix #{idx}[/bold]" + (f" — {description}" if description else ""))
        if file_path:
            console.print(f"  [dim]File:[/dim] {file_path}")

        console.print()
        console.print(
            Panel(
                Syntax(new_code, _guess_lang(file_path), theme="monokai", line_numbers=True),
                title=f"[yellow]Proposed Change #{idx}[/yellow]",
                border_style="yellow",
            )
        )

        console.print(
            "\n[bold]Apply this fix?[/bold] [dim](y = yes / n = skip / q = quit)[/dim] ",
            end="",
        )
        try:
            ans = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Aborted.[/yellow]")
            break

        if ans == "q":
            console.print("[yellow]Quit — no further fixes applied.[/yellow]")
            break
        if ans != "y":
            console.print(f"  [dim]Skipped fix #{idx}.[/dim]")
            continue

        if not file_path or not Path(file_path).exists():
            console.print(
                f"  [yellow]Cannot apply:[/yellow] "
                f"file path {'not found' if file_path else 'not specified'}. "
                "Apply manually."
            )
            continue

        target = Path(file_path)
        original = target.read_text(encoding="utf-8")

        # Backup
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = target.with_suffix(f".{ts}.bak")
        shutil.copy2(target, bak)
        console.print(f"  [dim]Backup: {bak}[/dim]")

        # Apply
        patched = _apply_fix(original, new_code)
        if patched == original:
            console.print(f"  [yellow]Warning:[/yellow] patch did not match — apply manually.")
        else:
            target.write_text(patched, encoding="utf-8")
            console.print(f"  [green]Fix #{idx} applied.[/green]")
            applied += 1

    console.print()
    if applied:
        console.print(
            f"[bold green]{applied}[/bold green] / {len(fixes)} fix(es) applied.\n"
            "[dim]Review changes:  git diff\n"
            "Revert a file:   git checkout -- <file>[/dim]"
        )
    else:
        console.print("[dim]No fixes applied.[/dim]")
        _show_manual_hint()


def _extract_fixes(output: str, diff_result) -> list[tuple[str | None, str, str]]:
    """
    Parse ai_fixes agent output into (file_path, new_code, description) tuples.

    Looks for:
      File: path/to/file.py
      After:
      ```python
      <new code>
      ```
    or any annotated code block near a "File:" line.
    """
    fixes: list[tuple[str | None, str, str]] = []

    # Split by "Fix N:" or "##" section markers
    sections = re.split(r"(?:^|\n)(?:Fix\s*\d+[:\.]?|#{1,3}\s)", output)

    for section in sections:
        if not section.strip():
            continue

        # File path
        file_match = _FIX_FILE_RE.search(section)
        file_path_raw = file_match.group(1).strip() if file_match else None

        # Resolve relative file path against repo root
        file_path: str | None = None
        if file_path_raw:
            candidate = Path(file_path_raw)
            if not candidate.is_absolute():
                # Try relative to repo root
                try:
                    import subprocess as sp
                    root = sp.run(
                        ["git", "rev-parse", "--show-toplevel"],
                        capture_output=True, text=True, timeout=3,
                    ).stdout.strip()
                    abs_path = Path(root) / candidate
                    if abs_path.exists():
                        file_path = str(abs_path)
                except Exception:
                    pass
            if not file_path and candidate.exists():
                file_path = str(candidate.resolve())

        # Prefer "After:" block, fall back to any code block
        code_blocks = _AFTER_BLOCK_RE.findall(section) or _CODE_BLOCK_RE.findall(section)
        for block in code_blocks:
            block = block.strip()
            if block:
                # Description: first non-empty line of section before code
                desc_lines = [
                    l.strip() for l in section.split("```")[0].splitlines()
                    if l.strip() and not l.strip().startswith("File:")
                ]
                description = desc_lines[0][:80] if desc_lines else ""
                fixes.append((file_path, block, description))
                break  # one fix per section

    return fixes


def _apply_fix(original: str, new_code: str) -> str:
    """
    Replace matching content in original with new_code.
    Uses first 3 non-blank lines as a fingerprint.
    """
    block_lines = [l for l in new_code.splitlines() if l.strip()]
    if not block_lines:
        return original

    fingerprint = block_lines[0].strip()
    orig_lines = original.splitlines(keepends=True)

    for i, line in enumerate(orig_lines):
        if fingerprint in line:
            end = min(i + len(block_lines), len(orig_lines))
            new_lines = (
                list(orig_lines[:i])
                + [l + "\n" for l in block_lines]
                + list(orig_lines[end:])
            )
            return "".join(new_lines)

    return original


def _guess_lang(file_path: str | None) -> str:
    if not file_path:
        return "text"
    ext = Path(file_path).suffix.lstrip(".")
    return {
        "py": "python", "js": "javascript", "ts": "typescript",
        "go": "go", "rs": "rust", "java": "java", "rb": "ruby",
        "sh": "bash", "yaml": "yaml", "yml": "yaml", "json": "json",
    }.get(ext, "text")


def _wait_to_close() -> None:
    """
    When running in a new terminal window (headless hook), pause before exiting
    so the window doesn't snap closed immediately.  Skip if stdin is not a tty
    (e.g. piped / test mode).
    """
    try:
        if not sys.stdout.isatty():
            return
        console.print("\n[dim]Press Enter to close this window…[/dim]")
        input()
    except (EOFError, KeyboardInterrupt, OSError):
        pass


def _install_shutdown_handler() -> None:
    """
    Force-exit when the terminal window is closed or the parent process dies.

    Without this, Python waits for background threads (Ollama HTTP calls) to
    finish (up to 120 s) before exiting.  Using os._exit() bypasses that.

    SIGBREAK is the Windows CTRL_CLOSE_EVENT (sent when the CMD/WT window is
    closed). SIGTERM covers Linux/macOS process termination.
    """
    import os
    import signal

    def _force_exit(sig, frame):
        os._exit(0)

    try:
        signal.signal(signal.SIGTERM, _force_exit)
    except (OSError, ValueError, AttributeError):
        pass

    if sys.platform == "win32":
        try:
            # SIGBREAK = CTRL_BREAK_EVENT; also covers CTRL_CLOSE_EVENT
            signal.signal(signal.SIGBREAK, _force_exit)
        except (OSError, ValueError, AttributeError):
            pass


def _reopen_stdin() -> None:
    """
    Reconnect stdin to the controlling terminal.

    Git hooks redirect stdin to /dev/null, which makes every input() call
    raise EOFError immediately.  Only reopen when stdin is NOT already a tty —
    e.g. don't touch it when running inside a new CMD window where stdin is
    already the terminal.
    """
    try:
        if sys.stdin.isatty():
            return  # already connected — nothing to do
    except Exception:
        pass

    try:
        if sys.platform == "win32":
            # Use UTF-8 so typing works correctly in Windows Terminal / CMD
            sys.stdin = open("CON:", "r", encoding="utf-8", errors="replace")
        else:
            sys.stdin = open("/dev/tty", "r")
    except Exception:
        pass  # if it fails, EOFError will be caught in the caller


def _show_manual_hint() -> None:
    console.print(
        "\n[dim]To apply fixes manually:\n"
        "  nexarq run --agents ai_fixes > fixes.txt\n"
        "  nexarq apply --fix-file fixes.txt --target <file>[/dim]"
    )


def _print_missing_framework_error(fw: str, exc: ImportError) -> None:
    """Show a clean, user-friendly error when a framework package is not installed."""
    from rich.panel import Panel

    _INSTALL_HINTS: dict[str, str] = {
        "langgraph":  'pip install "nexarq-cli[langchain]"',
        "langchain":  'pip install "nexarq-cli[langchain]"',
        "crewai":     'pip install "nexarq-cli[crewai]"',
        "autogen":    'pip install "nexarq-cli[autogen]"',
    }
    _WHAT: dict[str, str] = {
        "langgraph":  "LangGraph + LangChain",
        "langchain":  "LangChain",
        "crewai":     "CrewAI",
        "autogen":    "AutoGen",
    }

    install_cmd = _INSTALL_HINTS.get(fw, 'pip install "nexarq-cli[frameworks]"')
    what = _WHAT.get(fw, fw)
    missing_pkg = str(exc).replace("No module named ", "").strip("'\"")

    body = (
        f"[bold red]Missing package:[/bold red] [yellow]{missing_pkg}[/yellow]\n\n"
        f"The [bold]{fw}[/bold] framework requires [bold]{what}[/bold] to be installed.\n\n"
        f"[bold]Install it with:[/bold]\n\n"
        f"  [cyan]{install_cmd}[/cyan]\n\n"
        f"Or install all frameworks at once:\n\n"
        f'  [cyan]pip install "nexarq-cli[frameworks]"[/cyan]\n\n'
        f"[dim]Then retry:[/dim]  [cyan]nexarq run --framework {fw}[/cyan]\n\n"
        f"[dim]Run [bold]nexarq doctor[/bold] to see what else may be missing.\n"
        f"Run [bold]nexarq doctor --fix[/bold] to auto-install everything.[/dim]"
    )

    console.print(
        Panel(
            body,
            title=f"[bold red] Framework Not Installed: {fw} [/bold red]",
            border_style="red",
            padding=(1, 2),
        )
    )



# ── Agent listing ─────────────────────────────────────────────────────────────

def _print_agents() -> None:
    from rich.table import Table
    from rich import box

    table = Table(title="Available Agents", box=box.ROUNDED, header_style="bold blue")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Default Severity")

    for name, desc in sorted(REGISTRY.descriptions().items()):
        agent = REGISTRY.get(name)
        sev = str(agent.severity.value if hasattr(agent.severity, "value") else agent.severity)
        table.add_row(name, desc, sev)

    console.print(table)
