"""nexarq init – guided project initialization wizard."""
from __future__ import annotations

import typer
from rich.prompt import Confirm, Prompt

from nexarq_cli.config.manager import ConfigManager
from nexarq_cli.config.schema import NexarqConfig, ProviderConfig, ProviderName
from nexarq_cli.git.hooks import HookInstaller
from nexarq_cli.security.secrets import SecretsManager
from nexarq_cli.utils.console import console

app = typer.Typer()


@app.command()
def init(
    non_interactive: bool = typer.Option(
        False, "--yes", "-y", help="Skip prompts and use defaults"
    ),
) -> None:
    """Initialize Nexarq CLI for the current project."""
    console.print("\n[bold blue]Nexarq CLI – Project Setup Wizard[/bold blue]\n")

    mgr = ConfigManager()
    mgr.ensure_dirs()
    cfg = mgr.load()

    if not non_interactive:
        _run_wizard(cfg, mgr)
    else:
        mgr.save(cfg)
        console.print("[green]OK[/green] Initialized with default settings.")

    console.print(
        f"\n[green]OK[/green] Config saved to [bold]{mgr.config_path}[/bold]"
    )
    console.print("[dim]Run [bold]nexarq doctor[/bold] to verify your setup.[/dim]\n")


def _run_wizard(cfg: NexarqConfig, mgr: ConfigManager) -> None:
    secrets = SecretsManager()

    # ── Provider selection ────────────────────────────────────────────────
    console.print("[bold]Step 1: LLM Provider[/bold]")
    console.print(
        "Choose your default provider:\n"
        "  [cyan]1[/cyan] ollama    (local – no data leaves your machine)\n"
        "  [cyan]2[/cyan] openai    (cloud – requires API key + consent)\n"
        "  [cyan]3[/cyan] anthropic (cloud – requires API key + consent)\n"
        "  [cyan]4[/cyan] google    (cloud – requires API key + consent)\n"
    )
    choice = Prompt.ask("Provider", choices=["1", "2", "3", "4"], default="1")
    provider_map = {"1": "ollama", "2": "openai", "3": "anthropic", "4": "google"}
    provider_name = provider_map[choice]

    # Discover available models at runtime instead of hardcoding
    model_default = _discover_default_model(provider_name)
    model = Prompt.ask("Model name", default=model_default)
    cfg.providers["default"] = ProviderConfig(name=ProviderName(provider_name), model=model)

    # API key for cloud providers
    if provider_name != "ollama":
        console.print(
            f"\n[yellow]WARN[/yellow] Cloud provider selected. "
            f"Data will be sent to {provider_name.capitalize()} servers."
        )
        consent = Confirm.ask("I consent to sending code diffs to the cloud provider", default=False)
        if consent:
            cfg.privacy.cloud_consent = True
            api_key = Prompt.ask(f"{provider_name.capitalize()} API key", password=True)
            if api_key:
                secrets.set_key(provider_name, api_key)
                console.print("[green]OK[/green] API key stored securely.")
        else:
            console.print("[yellow]Switching back to ollama (local).[/yellow]")
            cfg.providers["default"] = ProviderConfig(name=ProviderName.OLLAMA, model="")

    # ── Default agents ────────────────────────────────────────────────────
    console.print("\n[bold]Step 2: Default Agents[/bold]")
    console.print(
        "Leave empty for [bold]automatic selection[/bold] based on each commit's context.\n"
        "Or specify a comma-separated list to always run those agents."
    )
    agents_input = Prompt.ask(
        "Agents (empty = auto-select per commit)",
        default="",
    )
    cfg.default_agents = [a.strip() for a in agents_input.split(",") if a.strip()]

    # ── Git hooks ─────────────────────────────────────────────────────────
    console.print("\n[bold]Step 3: Git Hooks[/bold]")
    install_hooks = Confirm.ask("Install post-commit Git hook?", default=True)
    if install_hooks:
        try:
            installer = HookInstaller()
            path = installer.install("post-commit")
            console.print(f"[green]OK[/green] Installed hook at {path}")
        except Exception as e:
            console.print(f"[yellow]WARN[/yellow] Could not install hook: {e}")

    mgr.save(cfg)


def _discover_default_model(provider: str) -> str:
    """Query the provider at runtime to find the best available model."""
    if provider == "ollama":
        try:
            import httpx
            r = httpx.get("http://localhost:11434/api/tags", timeout=5)
            if r.status_code == 200:
                models = r.json().get("models", [])
                if models:
                    preferred_keywords = [
                        "kimi", "deepseek-coder", "codellama", "qwen2.5-coder",
                        "codegemma", "starcoder", "granite-code",
                    ]
                    all_names = [m["name"] for m in models]
                    for kw in preferred_keywords:
                        for name in all_names:
                            if kw in name.lower():
                                return name
                    return all_names[0]
        except Exception:
            pass
        return ""   # Empty = auto-discover at run time

    defaults = {
        "openai": "gpt-4o",
        "anthropic": "claude-sonnet-4-6",
        "google": "gemini-1.5-pro",
    }
    return defaults.get(provider, "")
