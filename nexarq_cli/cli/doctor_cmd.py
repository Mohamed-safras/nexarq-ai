"""nexarq doctor – system health check."""
from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
from typing import Optional

import typer
from rich.table import Table
from rich import box

from nexarq_cli.config.manager import ConfigManager
from nexarq_cli.security.secrets import SecretsManager
from nexarq_cli.utils.console import console

app = typer.Typer()

_REQUIRED_PACKAGES: list[tuple[str, str]] = [
    ("typer",     "typer>=0.12.0"),
    ("rich",      "rich>=13.7.0"),
    ("git",       "gitpython>=3.1.40"),
    ("httpx",     "httpx>=0.27.0"),
    ("pydantic",  "pydantic>=2.7.0"),
    ("yaml",      "pyyaml>=6.0.1"),
    ("dotenv",    "python-dotenv>=1.0.1"),
]

# (import_name, pip_package, purpose, group_label)
_OPTIONAL_PACKAGES: list[tuple[str, str, str, str]] = [
    ("keyring",              "keyring>=25.2.0",              "Secure API key storage",                     "security"),
    ("cryptography",         "cryptography>=42.0.0",         "Encrypted vault fallback",                   "security"),
    ("tenacity",             "tenacity>=8.3.0",              "Retry logic for LLM calls",                  "core"),
    ("ollama",               "ollama>=0.3.0",                "Local Ollama provider",                      "providers"),
    ("openai",               "openai>=1.40.0",               "OpenAI / compatible API provider",           "providers"),
    ("anthropic",            "anthropic>=0.34.0",            "Anthropic Claude provider",                  "providers"),
    ("google.genai",         "google-genai>=1.0.0",          "Google Gemini provider",                     "providers"),
    ("langchain_core",       "nexarq-cli[langchain]",        "LangChain LCEL chains + CoT",                "frameworks"),
    ("langgraph",            "nexarq-cli[langchain]",        "LangGraph StateGraph orchestration",         "frameworks"),
    ("langchain_ollama",     "nexarq-cli[langchain]",        "LangChain-Ollama bridge",                    "frameworks"),
    ("langchain_openai",     "nexarq-cli[langchain]",        "LangChain-OpenAI bridge",                    "frameworks"),
    ("langchain_anthropic",  "nexarq-cli[langchain]",        "LangChain-Anthropic bridge",                 "frameworks"),
    ("crewai",               "nexarq-cli[crewai]",           "CrewAI role-based crews",                    "frameworks"),
    ("autogen",              "nexarq-cli[autogen]",          "AutoGen 2-agent chat per review",            "frameworks"),
]

# Pip extras that install multiple packages at once
_GROUP_INSTALL_HINT = {
    "frameworks": "pip install -e \".[frameworks]\"  (installs langchain + langgraph + crewai + autogen)",
    "providers":  "pip install -e \".[all]\"",
    "security":   "pip install keyring cryptography",
    "core":       "pip install tenacity",
}


@app.command()
def doctor(
    fix: bool = typer.Option(
        False, "--fix", "-f",
        help="Automatically install all missing packages.",
    ),
) -> None:
    """Check your Nexarq CLI installation and configuration."""
    console.print("\n[bold blue]Nexarq Doctor – System Health Check[/bold blue]\n")

    all_ok = True
    missing_optional: list[tuple[str, str, str]] = []   # (import_name, pip_pkg, group)

    # ── Python version ────────────────────────────────────────────────────
    py_ver = sys.version_info
    ok = py_ver >= (3, 10)
    _row("Python version", f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}", ok)
    if not ok:
        console.print("  [red]Python 3.10+ is required. Please upgrade Python.[/red]")
        all_ok = False

    # ── Required packages ─────────────────────────────────────────────────
    console.print("\n[bold]Core Dependencies:[/bold]")
    req_table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    req_table.add_column("Package")
    req_table.add_column("Status")
    req_table.add_column("Fix")

    for import_name, pip_pkg in _REQUIRED_PACKAGES:
        try:
            importlib.import_module(import_name)
            req_table.add_row(import_name, "[green]installed[/green]", "")
        except ImportError:
            req_table.add_row(
                import_name,
                "[red]MISSING[/red]",
                f"pip install {pip_pkg}",
            )
            all_ok = False

    console.print(req_table)

    if not all_ok:
        console.print(
            "  [red bold]Core packages are missing. Run:[/red bold]\n"
            "  [cyan]pip install nexarq-cli[/cyan]\n"
        )

    # ── Optional packages ─────────────────────────────────────────────────
    console.print("[bold]Optional Dependencies:[/bold]")
    opt_table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    opt_table.add_column("Package")
    opt_table.add_column("Status")
    opt_table.add_column("Purpose")
    opt_table.add_column("Install")

    for import_name, pip_pkg, purpose, group in _OPTIONAL_PACKAGES:
        try:
            importlib.import_module(import_name)
            opt_table.add_row(import_name, "[green]installed[/green]", purpose, "")
        except ImportError:
            opt_table.add_row(
                import_name,
                "[yellow]not installed[/yellow]",
                purpose,
                f"[dim]{pip_pkg}[/dim]",
            )
            missing_optional.append((import_name, pip_pkg, group))

    console.print(opt_table)

    # Show grouped install hints for missing optional packages
    if missing_optional:
        missing_groups = {grp for _, _, grp in missing_optional}
        console.print("[bold yellow]To install missing optional packages:[/bold yellow]")

        if "frameworks" in missing_groups:
            console.print(f"  [cyan]pip install \"nexarq-cli[frameworks]\"[/cyan]   # langchain + langgraph + crewai + autogen")
        if "providers" in missing_groups:
            console.print(f"  [cyan]pip install \"nexarq-cli[all]\"[/cyan]           # all LLM provider SDKs")
        if "security" in missing_groups:
            console.print(f"  [cyan]pip install keyring cryptography[/cyan]")
        if "core" in missing_groups:
            console.print(f"  [cyan]pip install tenacity[/cyan]")
        console.print(f"  [cyan]pip install \"nexarq-cli[all]\"[/cyan]              # install everything at once")
        console.print()

        # Auto-fix mode
        if fix:
            from nexarq_cli.utils.autodeps import resolve_all
            resolve_all()
            console.print("\n[bold green]All packages installed.[/bold green]  Run [cyan]nexarq doctor[/cyan] to verify.\n")
        else:
            console.print(
                "  [dim]Tip: run [bold]nexarq doctor --fix[/bold] to install all missing packages automatically.[/dim]\n"
            )

    # ── Config ────────────────────────────────────────────────────────────
    console.print("[bold]Configuration:[/bold]")
    mgr = ConfigManager()
    if mgr.config_path.exists():
        try:
            cfg = mgr.load()
            _row("Config file", str(mgr.config_path), True)
            provider_val = cfg.providers.get("default")
            provider_name = provider_val.name if provider_val and hasattr(provider_val, "name") else str(provider_val or "unknown")
            _row("Default provider", provider_name, True)
            _row("Default agents", ", ".join(cfg.default_agents) if cfg.default_agents else "(all)", True)
            _row("Cloud consent", str(cfg.privacy.cloud_consent), True)
        except Exception as e:
            _row("Config file", f"ERROR: {e}", False)
            all_ok = False
    else:
        _row("Config file", "not found — run: nexarq init", False)
        console.print("  [yellow]Run [bold]nexarq init[/bold] to create your configuration.[/yellow]")

    # ── API keys ──────────────────────────────────────────────────────────
    console.print("\n[bold]API Keys:[/bold]")
    secrets = SecretsManager()
    for provider in ["openai", "anthropic", "google"]:
        has_key = secrets.has_key(provider)
        _row(f"{provider} key", "configured" if has_key else "not set", True)

    if not any(secrets.has_key(p) for p in ["openai", "anthropic", "google"]):
        console.print(
            "  [dim]No cloud API keys set — using Ollama (local) only.\n"
            "  To add a key: [bold]nexarq config set-key openai <your-key>[/bold][/dim]"
        )

    # ── Git ───────────────────────────────────────────────────────────────
    console.print("\n[bold]Git:[/bold]")
    git_path = shutil.which("git")
    git_ok = git_path is not None
    _row("git binary", git_path or "not found", git_ok)
    if not git_ok:
        all_ok = False
        console.print("  [red]Git is required. Install from https://git-scm.com[/red]")

    global_hooks_path = _get_global_hooks_path()
    if global_hooks_path:
        _row("hooks scope", f"global  ({global_hooks_path})", True)
        from pathlib import Path
        for hook in ("post-commit", "pre-push"):
            hp = Path(global_hooks_path) / hook
            if hp.exists():
                content = hp.read_text(encoding="utf-8", errors="ignore")
                state = "nexarq" if "Nexarq" in content else "other"
            else:
                state = "not installed"
            _row(f"{hook} hook", state, state in ("nexarq", "not installed"))
    else:
        _row("hooks scope", "local (no global hooks set)", True)
        try:
            from nexarq_cli.git.hooks import HookInstaller
            installer = HookInstaller()
            status = installer.status()
            for hook, state in status.items():
                _row(f"{hook} hook", state, state in ("nexarq", "not installed"))
        except Exception:
            pass

    # ── Ollama ────────────────────────────────────────────────────────────
    console.print("\n[bold]Ollama (local LLM):[/bold]")
    ollama_up, ollama_models = _check_ollama()
    _row("Ollama server", "running" if ollama_up else "not reachable (optional)", True)
    if ollama_up and ollama_models:
        console.print(f"  [dim]Available models: {', '.join(ollama_models[:5])}[/dim]")
    elif not ollama_up:
        console.print(
            "  [dim]Ollama not running — only cloud providers will work.\n"
            "  To start: [bold]ollama serve[/bold][/dim]"
        )

    # ── Result ────────────────────────────────────────────────────────────
    console.print()
    if all_ok and not missing_optional:
        console.print("[bold green]All checks passed. Nexarq is fully ready![/bold green]")
    elif all_ok:
        console.print(
            "[bold green]Core checks passed.[/bold green] "
            "[yellow]Some optional frameworks are not installed "
            "(needed only for --framework langgraph/crewai/autogen).[/yellow]"
        )
    else:
        console.print("[bold red]Some required checks failed. See above for remediation.[/bold red]")
        raise typer.Exit(1)



def _row(label: str, value: str, ok: bool) -> None:
    icon = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
    console.print(f"  [{icon}] [bold]{label}:[/bold] {value}")


def _get_global_hooks_path() -> str | None:
    try:
        r = subprocess.run(
            ["git", "config", "--global", "core.hooksPath"],
            capture_output=True, text=True,
        )
        val = r.stdout.strip()
        return val if val else None
    except Exception:
        return None


def _check_ollama() -> tuple[bool, list[str]]:
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        if r.status_code == 200:
            data = r.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return True, models
        return False, []
    except Exception:
        return False, []
