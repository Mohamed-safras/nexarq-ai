"""
Automatic dependency resolver for Nexarq CLI.

When any import fails, this module:
1. Identifies which pip package is needed
2. Installs it silently with a spinner
3. Re-execs the original process so the user's command runs as if nothing happened

End users never need to run pip manually.
"""
from __future__ import annotations

import os
import subprocess
import sys
from importlib.metadata import version as pkg_version, PackageNotFoundError

# Maps Python import names → pip package specifiers
# Key = top-level module name (what you'd import)
# Value = what to pass to pip install
_IMPORT_TO_PIP: dict[str, str] = {
    # Core CLI
    "typer":                "typer>=0.12.0",
    "rich":                 "rich>=13.7.0",
    "pydantic":             "pydantic>=2.7.0",
    "pydantic_settings":    "pydantic-settings>=2.3.0",
    "httpx":                "httpx>=0.27.0",
    "yaml":                 "pyyaml>=6.0.1",
    "dotenv":               "python-dotenv>=1.0.1",
    "git":                  "gitpython>=3.1.40",
    "keyring":              "keyring>=25.2.0",
    "cryptography":         "cryptography>=42.0.0",
    "tenacity":             "tenacity>=8.3.0",
    # LLM providers
    "openai":               "openai>=1.40.0",
    "anthropic":            "anthropic>=0.34.0",
    "google":               "google-genai>=1.0.0",
    "ollama":               "ollama>=0.3.0",
    # LangChain / LangGraph family — one extra installs all of them
    "langchain":            "nexarq-cli[langchain]",
    "langchain_core":       "nexarq-cli[langchain]",
    "langchain_ollama":     "nexarq-cli[langchain]",
    "langchain_openai":     "nexarq-cli[langchain]",
    "langchain_anthropic":  "nexarq-cli[langchain]",
    "langchain_google_genai": "nexarq-cli[langchain]",
    "langgraph":            "nexarq-cli[langchain]",
    # CrewAI
    "crewai":               "nexarq-cli[crewai]",
    # AutoGen
    "autogen":              "nexarq-cli[autogen]",
    "pyautogen":            "nexarq-cli[autogen]",
}

# Human-readable names for the spinner message
_FRIENDLY: dict[str, str] = {
    "nexarq-cli[langchain]": "LangGraph + LangChain",
    "nexarq-cli[crewai]":    "CrewAI",
    "nexarq-cli[autogen]":   "AutoGen",
    "nexarq-cli[frameworks]":"all AI frameworks",
    "openai>=1.40.0":        "OpenAI",
    "anthropic>=0.34.0":     "Anthropic",
    "google-genai>=1.0.0":   "Google Gemini",
    "ollama>=0.3.0":         "Ollama",
}


def resolve(exc: ImportError) -> None:
    """
    Called whenever an ImportError is caught anywhere in the CLI.

    Installs the required package and re-execs the process with the same
    arguments so the user's original command runs transparently.
    """
    missing_mod = str(exc).replace("No module named ", "").strip("'\"")
    top = missing_mod.split(".")[0]

    pip_pkg = _IMPORT_TO_PIP.get(missing_mod) or _IMPORT_TO_PIP.get(top)

    if pip_pkg is None:
        # Unknown package — derive a best-guess pip name
        pip_pkg = top.replace("_", "-")

    friendly = _FRIENDLY.get(pip_pkg, pip_pkg)

    _install(friendly, pip_pkg)
    _reexec()


def resolve_all() -> None:
    """
    Install every optional extra at once.
    Called by `nexarq doctor --fix` or `nexarq install`.
    """
    extras = ["langchain", "crewai", "autogen"]
    for extra in extras:
        pip_pkg = f"nexarq-cli[{extra}]"
        friendly = _FRIENDLY.get(pip_pkg, pip_pkg)
        _install(friendly, pip_pkg)


def _install(friendly: str, pip_pkg: str) -> None:
    """Run pip install, showing a clean status line. Never show a traceback."""
    try:
        from rich.console import Console
        from rich.status import Status
        _console = Console()
    except ImportError:
        # Rich not yet installed — fall back to plain print
        _console = None  # type: ignore[assignment]

    if _console:
        _console.print(
            f"\n  [bold blue]Setting up:[/bold blue] {friendly}  "
            f"[dim](this happens once)[/dim]"
        )
        with Status(
            f"  [dim]Installing {pip_pkg}…[/dim]",
            console=_console,
            spinner="dots",
        ):
            ok, err = _run_pip(pip_pkg)
    else:
        print(f"\n  Setting up: {friendly} (this happens once)")
        print(f"  Installing {pip_pkg}…")
        ok, err = _run_pip(pip_pkg)

    if ok:
        if _console:
            _console.print(f"  [bold green]Ready:[/bold green] {friendly}\n")
        else:
            print(f"  Ready: {friendly}\n")
    else:
        if _console:
            _console.print(
                f"\n  [bold red]Could not install {friendly}.[/bold red]\n"
                f"  {err}\n\n"
                f"  If this keeps failing, run:\n"
                f"    pip install \"{pip_pkg}\"\n"
            )
        else:
            print(f"\n  Could not install {pip_pkg}: {err}")
        sys.exit(1)


def _run_pip(pip_pkg: str) -> tuple[bool, str]:
    """Run pip install quietly. Returns (success, error_message)."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", pip_pkg],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True, ""
    # Return last non-empty line of stderr as the error
    lines = [l for l in result.stderr.splitlines() if l.strip()]
    return False, lines[-1] if lines else "unknown error"


def _reexec() -> None:
    """
    Replace the current process with a fresh copy running the same command.

    This is the cleanest way to make a newly-installed package available:
    restart the interpreter from scratch instead of trying to hot-reload modules.
    """
    # os.execv replaces the current process — nothing after this line runs
    try:
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except OSError:
        # execv not available (e.g. some Windows edge cases) — subprocess fallback
        result = subprocess.run([sys.executable] + sys.argv)
        sys.exit(result.returncode)
