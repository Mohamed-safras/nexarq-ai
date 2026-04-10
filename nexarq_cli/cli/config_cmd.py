"""nexarq config – view and modify configuration."""
from __future__ import annotations

import typer
import yaml
from rich.panel import Panel
from rich.syntax import Syntax

from nexarq_cli.config.manager import ConfigManager
from nexarq_cli.config.schema import ProviderConfig, ProviderName
from nexarq_cli.security.secrets import SecretsManager
from nexarq_cli.utils.console import console

app = typer.Typer(help="View and modify Nexarq configuration.")


@app.command("show")
def show(
    profile: str = typer.Option("default", help="Profile to show"),
) -> None:
    """Display the current configuration."""
    mgr = ConfigManager(profile=profile)
    cfg = mgr.load()
    raw = cfg.model_dump(mode="json", exclude_none=True)
    syntax = Syntax(yaml.dump(raw, default_flow_style=False), "yaml", theme="monokai")
    console.print(Panel(syntax, title=f"Config: {mgr.config_path}", border_style="blue"))


@app.command("set-key")
def set_key(
    provider: str = typer.Argument(..., help="Provider name: openai, anthropic, google"),
    key: str = typer.Option(None, "--key", "-k", help="API key (omit to prompt securely)"),
) -> None:
    """Store an API key securely in the system keyring."""
    if key is None:
        from rich.prompt import Prompt
        key = Prompt.ask(f"{provider} API key", password=True)

    if not key:
        console.print("[red]Error:[/red] No key provided.")
        raise typer.Exit(1)

    SecretsManager().set_key(provider, key)
    console.print(f"[green]OK[/green] API key for [bold]{provider}[/bold] stored securely.")


@app.command("delete-key")
def delete_key(
    provider: str = typer.Argument(..., help="Provider name"),
) -> None:
    """Remove a stored API key."""
    SecretsManager().delete_key(provider)
    console.print(f"[green]OK[/green] API key for [bold]{provider}[/bold] removed.")


@app.command("set-provider")
def set_provider(
    name: str = typer.Argument(..., help="Provider: ollama, openai, anthropic, google"),
    model: str = typer.Option(None, "--model", "-m", help="Model name"),
    profile: str = typer.Option("default", help="Profile"),
) -> None:
    """Set the default LLM provider."""
    mgr = ConfigManager(profile=profile)
    cfg = mgr.load()
    model_defaults = {
        "ollama": "codellama",
        "openai": "gpt-4o",
        "anthropic": "claude-sonnet-4-6",
        "google": "gemini-1.5-pro",
    }
    cfg.providers["default"] = ProviderConfig(
        name=ProviderName(name),
        model=model or model_defaults.get(name, name),
    )
    mgr.save(cfg)
    console.print(f"[green]OK[/green] Default provider set to [bold]{name}[/bold].")


@app.command("set-agents")
def set_agents(
    agents: str = typer.Argument(..., help="Comma-separated agent names"),
    profile: str = typer.Option("default", help="Profile"),
) -> None:
    """Set the default agents to run."""
    mgr = ConfigManager(profile=profile)
    cfg = mgr.load()
    cfg.default_agents = [a.strip() for a in agents.split(",") if a.strip()]
    mgr.save(cfg)
    console.print(f"[green]OK[/green] Default agents: {', '.join(cfg.default_agents)}")


@app.command("cloud-consent")
def cloud_consent(
    enabled: bool = typer.Argument(..., help="true or false"),
    profile: str = typer.Option("default", help="Profile"),
) -> None:
    """Enable or disable cloud provider consent (PR-6)."""
    mgr = ConfigManager(profile=profile)
    cfg = mgr.load()
    cfg.privacy.cloud_consent = enabled
    mgr.save(cfg)
    status = "[green]enabled[/green]" if enabled else "[red]disabled[/red]"
    console.print(f"[green]OK[/green] Cloud consent: {status}")


@app.command("list-profiles")
def list_profiles() -> None:
    """List available configuration profiles."""
    mgr = ConfigManager()
    profiles = mgr.list_profiles()
    console.print("[bold]Available profiles:[/bold]")
    for p in profiles:
        console.print(f"  - {p}")


@app.command("add-standards")
def add_standards(
    path: str = typer.Argument(..., help="Path to standards file (.md or .txt)"),
    profile: str = typer.Option("default", help="Profile"),
) -> None:
    """Load project coding standards for the standards agent."""
    import shutil
    from pathlib import Path

    src = Path(path)
    if not src.exists():
        console.print(f"[red]Error:[/red] File not found: {path}")
        raise typer.Exit(1)

    mgr = ConfigManager(profile=profile)
    mgr.ensure_dirs()
    dest = mgr.home / "standards.md"
    shutil.copy(src, dest)
    console.print(f"[green]OK[/green] Standards loaded from [bold]{path}[/bold].")
    console.print(f"  Stored at: {dest}")
