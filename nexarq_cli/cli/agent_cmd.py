"""
nexarq coder — autonomous coding agent.

Works like Claude Code: reads files, writes code, runs tests,
documents changes — always asking before modifying anything.

Usage:
    nexarq coder "add input validation to the user endpoint"
    nexarq coder   (prompts interactively)

In interactive chat mode, use:
    /agent <task>
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

import typer

from nexarq_cli.utils.console import console

app = typer.Typer()


@app.command()
def agent(
    task: Optional[str] = typer.Argument(
        None, help="What you want the agent to do. Omit to type interactively."
    ),
    profile: str = typer.Option("default", "--profile", "-p", help="Config profile"),
    repo: Optional[str] = typer.Option(
        None, "--repo", "-r",
        help="Repo root (auto-detected from git if omitted)",
    ),
) -> None:
    """
    Autonomous coding agent — plan, code, test, document.

    The agent reads your codebase, drafts a plan, shows it to you,
    then executes step by step.  Every file write and command requires
    your explicit confirmation before it runs.

    Examples:
      nexarq agent "add error handling to app/api/routes.py"
      nexarq agent "write unit tests for the auth module"
      nexarq agent "refactor the database layer to use connection pooling"
      nexarq agent "document all public functions in app/utils/"
    """
    # ── Load provider ────────────────────────────────────────────────────────
    from nexarq_cli.config.manager import ConfigManager
    from nexarq_cli.agents.autonomous.executor import AutonomousAgent

    mgr = ConfigManager(profile=profile)

    # Auto-setup if not configured
    from nexarq_cli.cli.setup_wizard import is_configured, run_auto_setup
    if not is_configured(mgr.config_path):
        repo_root = _get_repo_root(repo)
        if not run_auto_setup(mgr.config_path, repo_root):
            return
        mgr.reset_cache()

    cfg = mgr.load()

    # ── Get task ──────────────────────────────────────────────────────────────
    if not task:
        console.print(
            "\n[bold cyan]Nexarq Coder[/bold cyan]  "
            "[dim]What would you like me to do?[/dim]\n"
        )
        console.print("[bold cyan]>[/bold cyan] ", end="")
        try:
            task = input().strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Cancelled.[/yellow]")
            return

    if not task:
        console.print("[yellow]No task provided.[/yellow]")
        return

    # ── Run agent ─────────────────────────────────────────────────────────────
    repo_root = _get_repo_root(repo)
    runner = AutonomousAgent(cfg=cfg, repo_root=repo_root)

    try:
        runner.run(task)
    except KeyboardInterrupt:
        console.print("\n[yellow]Agent interrupted.[/yellow]")


def _get_repo_root(override: str | None) -> Path:
    if override:
        return Path(override).resolve()

    git_dir = os.environ.get("GIT_DIR")
    if git_dir:
        p = Path(git_dir)
        return (p.parent if p.name == ".git" else p).resolve()

    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return Path(r.stdout.strip()).resolve()
    except Exception:
        pass

    return Path.cwd().resolve()
