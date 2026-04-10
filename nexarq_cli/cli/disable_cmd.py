"""nexarq disable – disable Nexarq globally or for current repository (SRS 3.10)."""
from __future__ import annotations

import typer

from nexarq_cli.config.manager import ConfigManager
from nexarq_cli.utils.console import console

app = typer.Typer()


@app.command()
def disable(
    global_scope: bool = typer.Option(
        False, "--global", "-g", help="Disable globally (default: current repo)"
    ),
    profile: str = typer.Option("default", "--profile", "-p", help="Config profile"),
) -> None:
    """Disable Nexarq code review for this repo or globally."""
    mgr = ConfigManager(profile=profile)
    cfg = mgr.load()

    cfg.enabled = False  # type: ignore[attr-defined]
    mgr.save(cfg)

    scope = "globally" if global_scope else f"for profile '{profile}'"
    console.print(f"[bold yellow]Nexarq disabled[/bold yellow] {scope}.")
    console.print(
        "  Git hooks will not trigger reviews.\n"
        "  Re-enable with: [bold]nexarq enable[/bold]"
    )
