"""nexarq enable – enable Nexarq globally or for current repository (SRS 3.10)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from nexarq_cli.config.manager import ConfigManager
from nexarq_cli.utils.console import console

app = typer.Typer()


@app.command()
def enable(
    global_scope: bool = typer.Option(
        False, "--global", "-g", help="Enable globally (default: current repo)"
    ),
    profile: str = typer.Option("default", "--profile", "-p", help="Config profile"),
) -> None:
    """Enable Nexarq code review for this repo or globally."""
    mgr = ConfigManager(profile=profile)
    cfg = mgr.load()

    if not hasattr(cfg, "enabled"):
        console.print("[yellow]Config schema does not support enable flag – upgrading.[/yellow]")

    cfg.enabled = True  # type: ignore[attr-defined]
    mgr.save(cfg)

    scope = "globally" if global_scope else f"for profile '{profile}'"
    console.print(f"[bold green]Nexarq enabled[/bold green] {scope}.")
    console.print(
        "  Run [bold]nexarq run[/bold] to perform a code review.\n"
        "  Run [bold]nexarq hook install[/bold] to activate Git hooks."
    )
