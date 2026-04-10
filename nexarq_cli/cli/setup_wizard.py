"""
Auto-setup wizard — runs when nexarq is installed but not yet configured.

Triggered automatically on the first commit (via hook) or first `nexarq run`.
Works in any terminal: VS Code integrated terminal, JetBrains terminal,
Windows Terminal, PowerShell, cmd, bash — anything with a TTY.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from nexarq_cli.utils.console import console


# ── Public API ────────────────────────────────────────────────────────────────

def is_configured(config_path: Path) -> bool:
    """Return True only if a real config file already exists on disk."""
    return config_path.exists()


def run_auto_setup(config_path: Path, repo_root: Path | None = None) -> bool:
    """
    Interactive first-time setup wizard.

    Scans the system for available LLM providers, shows a suggested config,
    and asks the user to confirm before writing anything.

    Returns True if setup completed and review should proceed.
    Returns False if the user cancelled.
    """
    console.print(
        Panel(
            "[bold]Nexarq is installed but not configured yet.[/bold]\n\n"
            "This wizard will set up Nexarq in under a minute.\n"
            "You can re-run it any time with [cyan]nexarq init[/cyan].",
            title="[bold blue]Nexarq — First Time Setup[/bold blue]",
            border_style="blue",
        )
    )
    console.print()

    # ── Scan system ───────────────────────────────────────────────────────
    console.print("  [dim]Scanning your environment…[/dim]\n")

    provider, model, base_url = _detect_provider()
    repo_root = repo_root or _detect_repo()

    # ── Show what we found ────────────────────────────────────────────────
    if provider == "ollama":
        console.print(f"  [green]✓[/green] Ollama running  →  model: [cyan]{model}[/cyan]")
    elif provider:
        console.print(f"  [green]✓[/green] {provider.capitalize()} API key detected  →  model: [cyan]{model}[/cyan]")
    else:
        console.print("  [yellow]![/yellow] No LLM provider found.")
        console.print("      Install Ollama (https://ollama.ai) or set an API key,")
        console.print("      then run [cyan]nexarq init[/cyan] to configure.\n")
        _show_install_hint()
        return False

    if repo_root:
        console.print(f"  [green]✓[/green] Git repo        →  [dim]{repo_root}[/dim]")

    editor = _detect_editor()
    if editor:
        console.print(f"  [green]✓[/green] Editor detected →  [dim]{editor}[/dim]")

    console.print()
    console.print("  [bold]Suggested configuration:[/bold]")
    console.print(f"    Provider  :  [cyan]{provider}[/cyan]")
    console.print(f"    Model     :  [cyan]{model}[/cyan]")
    console.print(f"    Review on :  post-commit  [dim](auto-review every commit)[/dim]")
    console.print()

    # ── Confirm ───────────────────────────────────────────────────────────
    try:
        ok = Confirm.ask("  Accept and start review?", default=True)
    except (EOFError, KeyboardInterrupt):
        console.print("\n[yellow]Setup cancelled.[/yellow]")
        return False

    if not ok:
        console.print(
            "\n[dim]Run [bold]nexarq init[/bold] to configure manually.[/dim]"
        )
        return False

    # ── Write config ──────────────────────────────────────────────────────
    _write_config(config_path, provider, model, base_url)
    console.print(f"\n  [green]✓[/green] Config saved  →  {config_path}")

    # ── Install hooks in current repo ─────────────────────────────────────
    if repo_root:
        try:
            from nexarq_cli.git.hooks import HookInstaller
            installer = HookInstaller(repo_root)
            installer.install("post-commit")
            console.print(f"  [green]✓[/green] Hook installed →  {repo_root / '.git' / 'hooks' / 'post-commit'}")
        except Exception as exc:
            console.print(f"  [yellow]![/yellow] Hook install skipped: {exc}")

    console.print()
    console.print("[bold green]Setup complete![/bold green] Starting review…\n")
    console.print("─" * 60)
    console.print()
    return True


# ── Detection helpers ─────────────────────────────────────────────────────────

def _detect_provider() -> tuple[str, str, str]:
    """
    Return (provider_name, model_name, base_url).
    Priority: Ollama (local, free) → OpenAI → Anthropic → Google.
    """
    # 1. Ollama — check if running locally
    ollama_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    models = _query_ollama(ollama_url)
    if models:
        model = _pick_ollama_model(models)
        return "ollama", model, ollama_url

    # 2. OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        return "openai", "gpt-4o", ""

    # 3. Anthropic
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic", "claude-sonnet-4-6", ""

    # 4. Google
    if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        return "google", "gemini-2.0-flash", ""

    return "", "", ""


def _query_ollama(base_url: str) -> list[str]:
    """Return list of model names from Ollama, or [] if unreachable."""
    try:
        import httpx
        resp = httpx.get(f"{base_url}/api/tags", timeout=3)
        if resp.status_code == 200:
            return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        pass
    return []


def _pick_ollama_model(models: list[str]) -> str:
    """Pick the best code-capable model from available Ollama models."""
    preferred_keywords = [
        "kimi-k2.5", "deepseek-coder", "qwen2.5-coder",
        "codellama", "starcoder", "codegemma", "granite-code",
        "llama3", "mistral", "phi",
    ]
    for kw in preferred_keywords:
        for m in models:
            if kw in m.lower():
                return m
    return models[0] if models else "codellama:latest"


def _detect_repo() -> Path | None:
    """Return git repo root if we're inside one."""
    git_dir = os.environ.get("GIT_DIR")
    if git_dir:
        p = Path(git_dir)
        work_tree = p.parent if p.name == ".git" else p
        if work_tree.exists():
            return work_tree.resolve()
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return Path(r.stdout.strip()).resolve()
    except Exception:
        pass
    return None


def _detect_editor() -> str:
    """Return the name of the code editor/terminal in use, if detectable."""
    checks = [
        (os.environ.get("TERM_PROGRAM") == "vscode",             "VS Code"),
        (os.environ.get("TERMINAL_EMULATOR", "").startswith("JetBrains"), "JetBrains IDE"),
        (os.environ.get("IDEA_INITIAL_DIRECTORY") is not None,   "JetBrains IDE"),
        (os.environ.get("VSCODE_GIT_ASKPASS_NODE") is not None,  "VS Code"),
        (os.environ.get("WT_SESSION") is not None,               "Windows Terminal"),
        (os.environ.get("TERM_PROGRAM") == "iTerm.app",          "iTerm2"),
    ]
    for condition, name in checks:
        if condition:
            return name
    return ""


# ── Config writer ─────────────────────────────────────────────────────────────

def _write_config(config_path: Path, provider: str, model: str, base_url: str) -> None:
    """Write a minimal but complete config file to disk."""
    import yaml

    providers: dict = {
        "default": {
            "name": provider,
            "model": model,
            "temperature": 0.2,
            "max_tokens": 4096,
            "timeout": 120,
        }
    }
    if base_url and provider == "ollama":
        providers["default"]["base_url"] = base_url

    cfg: dict = {
        "version": "1",
        "profile": "default",
        "enabled": True,
        "providers": providers,
        "agents": {},
        "default_agents": [],
        "mcp_servers": [],
        "git": {
            "post_commit": True,
            "pre_push": False,
            "diff_only": True,
            "exclude_patterns": ["*.lock", "*.min.js", "dist/*", "build/*"],
            "max_diff_lines": 5000,
        },
        "privacy": {"cloud_consent": False, "send_file_paths": False},
        "audit": {"enabled": True, "log_level": "info"},
        "token_budget": {"enabled": False, "max_tokens_per_run": 0},
    }

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.dump(cfg, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def _show_install_hint() -> None:
    console.print(
        Panel(
            "Install a local model (free, private):\n\n"
            "  1. Download Ollama: [cyan]https://ollama.ai[/cyan]\n"
            "  2. Pull a model:    [cyan]ollama pull qwen2.5-coder:7b[/cyan]\n"
            "  3. Run again:       [cyan]nexarq init[/cyan]\n\n"
            "Or set a cloud API key:\n"
            "  [cyan]set OPENAI_API_KEY=sk-...[/cyan]  (then nexarq init)",
            title="[yellow]No LLM Provider Found[/yellow]",
            border_style="yellow",
        )
    )
