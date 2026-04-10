"""nexarq mcp – manage MCP server registrations."""
from __future__ import annotations

import typer

from nexarq_cli.config.manager import ConfigManager
from nexarq_cli.config.schema import MCPServerConfig
from nexarq_cli.mcp.registry import MCPRegistry
from nexarq_cli.utils.console import console

app = typer.Typer(help="Manage MCP (Model Context Protocol) servers.")


@app.command("add")
def add(
    name: str = typer.Argument(..., help="Server name"),
    uri: str = typer.Argument(..., help="Server URI (e.g. http://localhost:8090)"),
    local: bool = typer.Option(True, "--local/--remote", help="Is this a local server?"),
    tools: str = typer.Option("", "--tools", help="Comma-separated allowed tools"),
    consent: bool = typer.Option(
        False, "--consent", help="Explicit consent for remote server (required for --remote)"
    ),
    profile: str = typer.Option("default", help="Config profile"),
) -> None:
    """Register a new MCP server."""
    if not local and not consent:
        console.print(
            "[red]Error:[/red] Remote MCP servers require --consent flag.\n"
            "This confirms you consent to network calls being made to the server."
        )
        raise typer.Exit(1)

    mgr = ConfigManager(profile=profile)
    cfg = mgr.load()
    registry = MCPRegistry(cfg)

    allowed_tools = [t.strip() for t in tools.split(",") if t.strip()]

    server = MCPServerConfig(
        name=name,
        uri=uri,
        local=local,
        allowed_tools=allowed_tools,
        consent_given=consent or local,
    )

    try:
        registry.register(server)
        mgr.save(cfg)
        console.print(f"[green]OK[/green] Registered MCP server [bold]{name}[/bold] at {uri}")
        if allowed_tools:
            console.print(f"  Allowed tools: {', '.join(allowed_tools)}")
        else:
            console.print("  [yellow]Warning:[/yellow] No tools allowed (set --tools to enable)")
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)


@app.command("remove")
def remove(
    name: str = typer.Argument(..., help="Server name to remove"),
    profile: str = typer.Option("default", help="Config profile"),
) -> None:
    """Unregister an MCP server."""
    mgr = ConfigManager(profile=profile)
    cfg = mgr.load()
    registry = MCPRegistry(cfg)

    if registry.unregister(name):
        mgr.save(cfg)
        console.print(f"[green]OK[/green] Removed MCP server [bold]{name}[/bold].")
    else:
        console.print(f"[yellow]WARN[/yellow] Server '{name}' not found.")


@app.command("list")
def list_servers(
    profile: str = typer.Option("default", help="Config profile"),
) -> None:
    """List registered MCP servers."""
    from rich.table import Table
    from rich import box

    mgr = ConfigManager(profile=profile)
    cfg = mgr.load()
    registry = MCPRegistry(cfg)
    servers = cfg.mcp_servers

    if not servers:
        console.print("[dim]No MCP servers registered.[/dim]")
        return

    table = Table(title="MCP Servers", box=box.ROUNDED, header_style="bold blue")
    table.add_column("Name")
    table.add_column("URI")
    table.add_column("Type")
    table.add_column("Enabled")
    table.add_column("Allowed Tools")

    for s in servers:
        table.add_row(
            s.name,
            s.uri,
            "[green]local[/green]" if s.local else "[yellow]remote[/yellow]",
            "[green]yes[/green]" if s.enabled else "[red]no[/red]",
            ", ".join(s.allowed_tools) or "[dim]none[/dim]",
        )

    console.print(table)
