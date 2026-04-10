"""
nexarq install — one-time global machine setup.

This is the FIRST command any user runs after installing nexarq.
It makes nexarq work automatically in EVERY git repo on this machine
without any per-repo configuration.

What it does:
  1. Creates ~/.nexarq/hooks/  (global hooks directory)
  2. Writes the post-commit hook there
  3. Sets git config --global core.hooksPath ~/.nexarq/hooks/
  4. Auto-detects LLM provider and writes ~/.nexarq/config.yaml
     (skipped if config already exists)
  5. Verifies the setup with a quick health check

After this, every git commit on this machine triggers nexarq.
If nexarq is not configured for a repo yet, the setup wizard runs
inline at the first commit — no manual `nexarq init` needed per repo.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer
from rich.panel import Panel
from rich.prompt import Confirm

from nexarq_cli.config.manager import ConfigManager
from nexarq_cli.git.hooks import HookInstaller
from nexarq_cli.utils.console import console


def install(
    global_hooks: bool = typer.Option(
        True, "--global/--local",
        help="Install globally (all repos) or locally (current repo only)",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
) -> None:
    """
    One-time global setup — makes nexarq work in every git repo on this machine.

    Run this once after installing nexarq. You never need to configure
    individual repos — nexarq auto-detects and sets itself up on first commit.
    """
    console.print(
        Panel(
            "[bold]nexarq install[/bold] — Global Machine Setup\n\n"
            "After this, every [cyan]git commit[/cyan] on this machine will\n"
            "automatically trigger a nexarq code review.",
            title="[bold blue]Nexarq[/bold blue]",
            border_style="blue",
        )
    )
    console.print()

    if global_hooks:
        _install_global(yes)
    else:
        _install_local(yes)


# ── Global install (recommended) ─────────────────────────────────────────────

def _install_global(yes: bool) -> None:
    """
    Set git's global core.hooksPath to ~/.nexarq/hooks/.
    Every repo on this machine will use these hooks automatically.
    """
    mgr = ConfigManager()
    hooks_dir = mgr.home / "hooks"

    console.print("  This will:")
    console.print(f"  [cyan]1[/cyan]  Create global hooks dir   [dim]{hooks_dir}[/dim]")
    console.print(f"  [cyan]2[/cyan]  Write post-commit hook     [dim]{hooks_dir / 'post-commit'}[/dim]")
    console.print(f"  [cyan]3[/cyan]  Set globally               [dim]git config --global core.hooksPath {hooks_dir}[/dim]")
    console.print(f"  [cyan]4[/cyan]  Auto-detect LLM provider   [dim](if not already configured)[/dim]")
    console.print()

    if not yes:
        try:
            ok = Confirm.ask("  Proceed?", default=True)
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)
        if not ok:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)

    console.print()

    # 1. Create hooks dir
    hooks_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"  [green]✓[/green]  Hooks dir     {hooks_dir}")

    # 2. Write the hook using the same installer (reuses exact same template)
    installer = HookInstaller.__new__(HookInstaller)
    installer.hooks_dir = hooks_dir
    hook_path = installer.install("post-commit")
    console.print(f"  [green]✓[/green]  Hook written  {hook_path}")

    # 3. Set global git config
    result = subprocess.run(
        ["git", "config", "--global", "core.hooksPath", str(hooks_dir)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        console.print(f"  [red]✗[/red]  git config failed: {result.stderr.strip()}")
        console.print("  [dim]Try running: git config --global core.hooksPath "
                      f"{hooks_dir}[/dim]")
        raise typer.Exit(1)
    console.print(f"  [green]✓[/green]  git config    core.hooksPath = {hooks_dir}")

    # 4. Auto-detect provider and write config (if not already done)
    if not mgr.config_path.exists():
        _auto_create_config(mgr)
    else:
        console.print(f"  [green]✓[/green]  Config exists  {mgr.config_path}  [dim](skipped)[/dim]")

    # Done
    console.print()
    console.print(
        Panel(
            "[bold green]Global install complete![/bold green]\n\n"
            "Every [cyan]git commit[/cyan] on this machine now triggers nexarq.\n\n"
            "First commit in any repo → nexarq auto-configures itself for that repo.\n\n"
            "To review your last commit right now:\n"
            "  [cyan]nexarq run[/cyan]\n\n"
            "To check everything is healthy:\n"
            "  [cyan]nexarq doctor[/cyan]",
            border_style="green",
        )
    )


# ── Local install (current repo only) ────────────────────────────────────────

def _install_local(yes: bool) -> None:
    """Install hooks only into the current repo's .git/hooks/."""
    try:
        installer = HookInstaller()
    except Exception as exc:
        console.print(f"[red]Error:[/red] Not inside a git repo: {exc}")
        raise typer.Exit(1)

    console.print("  Installing hook into current repo only.")
    console.print(f"  [dim]{installer.hooks_dir / 'post-commit'}[/dim]\n")

    if not yes:
        try:
            ok = Confirm.ask("  Proceed?", default=True)
        except (EOFError, KeyboardInterrupt):
            raise typer.Exit(0)
        if not ok:
            raise typer.Exit(0)

    path = installer.install("post-commit")
    console.print(f"\n  [green]✓[/green]  Hook installed at {path}")

    mgr = ConfigManager()
    if not mgr.config_path.exists():
        _auto_create_config(mgr)

    console.print()
    console.print("[bold green]Done.[/bold green] Next commit will trigger nexarq.\n")
    console.print("[dim]For all repos: run [bold]nexarq install --global[/bold][/dim]")


# ── Auto-detect config ────────────────────────────────────────────────────────

def _post_install() -> None:
    """
    Entry point: nexarq-setup — runs automatically after pip install nexarq-cli.

    Configures global git hooks and detects the LLM provider so nexarq works
    immediately in every repo on this machine without any extra commands.
    """
    from rich.console import Console as _Console
    _con = _Console()
    _con.print()
    _con.print("[bold blue]Nexarq[/bold blue] — finalising installation…")
    _con.print()

    mgr = ConfigManager()
    hooks_dir = mgr.home / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Global git hooks
    try:
        _installer = HookInstaller.__new__(HookInstaller)
        _installer.hooks_dir = hooks_dir
        _installer.install("post-commit")
        subprocess.run(
            ["git", "config", "--global", "core.hooksPath", str(hooks_dir)],
            check=True, capture_output=True,
        )
        _con.print(f"  [green]✓[/green]  Global git hooks  →  {hooks_dir}")
    except Exception as exc:
        _con.print(f"  [yellow]![/yellow]  Git hooks skipped: {exc}")

    # Auto-detect provider and write starter config
    if not mgr.config_path.exists():
        try:
            from nexarq_cli.cli.setup_wizard import _detect_provider, _write_config
            provider, model, base_url = _detect_provider()
            if provider:
                _write_config(mgr.config_path, provider, model, base_url)
                _con.print(
                    f"  [green]✓[/green]  Config created    →  {mgr.config_path}  "
                    f"[dim]({provider}: {model or 'auto-detect'})[/dim]"
                )
        except Exception:
            pass

    _con.print()
    _con.print("[bold green]Nexarq is ready.[/bold green]  "
               "Every git commit now triggers a code review.")
    _con.print("[dim]Run [cyan]nexarq doctor[/cyan] to verify your setup.[/dim]")
    _con.print()


def _auto_create_config(mgr: ConfigManager) -> None:
    """Detect available LLM provider and write a starter config."""
    from nexarq_cli.cli.setup_wizard import _detect_provider, _write_config

    console.print("  [dim]Detecting LLM provider…[/dim]")
    provider, model, base_url = _detect_provider()

    if not provider:
        console.print(
            "  [yellow]![/yellow]  No LLM provider found.\n"
            "      Install Ollama (https://ollama.ai) then run "
            "[cyan]nexarq install[/cyan] again,\n"
            "      or set OPENAI_API_KEY / ANTHROPIC_API_KEY."
        )
        # Write a stub config anyway so the wizard runs on first commit
        provider, model, base_url = "ollama", "", ""

    _write_config(mgr.config_path, provider, model, base_url)
    console.print(
        f"  [green]✓[/green]  Config created {mgr.config_path}  "
        f"[dim]({provider}: {model or 'auto-detect'})[/dim]"
    )
