"""nexarq hook – manage Git hooks."""
from __future__ import annotations

import typer

from nexarq_cli.git.hooks import HookInstaller
from nexarq_cli.utils.console import console

app = typer.Typer(help="Manage Nexarq Git hooks.")


@app.command("install")
def install(
    hook_type: str = typer.Argument(
        "post-commit",
        help="Hook type: post-commit or pre-push",
    ),
) -> None:
    """Install a Nexarq Git hook in the current repository."""
    if hook_type not in ("post-commit", "pre-push"):
        console.print(f"[red]Error:[/red] Unknown hook type: {hook_type}")
        console.print("Valid types: post-commit, pre-push")
        raise typer.Exit(1)

    try:
        installer = HookInstaller()
        path = installer.install(hook_type)
        console.print(f"[green]OK[/green] Installed [bold]{hook_type}[/bold] hook at:")
        console.print(f"  {path}")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


@app.command("uninstall")
def uninstall(
    hook_type: str = typer.Argument("post-commit", help="Hook type to remove"),
) -> None:
    """Remove a Nexarq Git hook."""
    try:
        installer = HookInstaller()
        removed = installer.uninstall(hook_type)
        if removed:
            console.print(f"[green]OK[/green] Removed [bold]{hook_type}[/bold] hook.")
        else:
            console.print(f"[yellow]WARN[/yellow] No Nexarq hook found for {hook_type}.")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


@app.command("status")
def status() -> None:
    """Show current Git hook status."""
    try:
        installer = HookInstaller()
        statuses = installer.status()

        console.print("\n[bold]Git Hook Status:[/bold]")
        for hook_type, state in statuses.items():
            if state == "nexarq":
                icon = "[green]OK[/green]"
                label = "[green]installed (nexarq)[/green]"
            elif state == "other":
                icon = "[yellow]--[/yellow]"
                label = "[yellow]installed (other)[/yellow]"
            else:
                icon = "[dim]--[/dim]"
                label = "[dim]not installed[/dim]"
            console.print(f"  {icon} {hook_type}: {label}")
        console.print()
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)
