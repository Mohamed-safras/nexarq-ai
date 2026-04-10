"""
Nexarq CLI – Entry point.

Any missing dependency is installed automatically and the process restarts.
Users never need to run pip manually.
"""
from __future__ import annotations

import sys
from pathlib import Path
from importlib.metadata import version as _pkg_version, PackageNotFoundError

# Ensure the project root is on sys.path when this file is run directly
# (e.g. `python nexarq_cli/main.py`).  Installed entry-points don't need this.
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ── Auto-resolve missing core packages before anything else loads ─────────────
try:
    from nexarq_cli.utils.autodeps import resolve as _resolve_dep
except ImportError:
    # autodeps itself had an import problem (extremely unlikely — it only uses stdlib)
    def _resolve_dep(exc):  # type: ignore[misc]
        print(f"\n  Missing: {exc}\n  Run:  pip install nexarq-cli\n")
        sys.exit(1)

try:
    import typer
    import rich  # noqa: F401
    import pydantic  # noqa: F401
    import httpx  # noqa: F401
except ImportError as _e:
    _resolve_dep(_e)   # installs + re-execs — never returns

# ── Now safe to import everything ─────────────────────────────────────────────
try:
    from nexarq_cli.cli.config_cmd import app as config_app
    from nexarq_cli.cli.hook_cmd import app as hook_app
    from nexarq_cli.cli.mcp_cmd import app as mcp_app
    from nexarq_cli.cli.apply_cmd import apply
    from nexarq_cli.cli.init_cmd import init
    from nexarq_cli.cli.doctor_cmd import doctor
    from nexarq_cli.cli.run_cmd import run
    from nexarq_cli.cli.help_cmd import help
    from nexarq_cli.cli.enable_cmd import enable
    from nexarq_cli.cli.disable_cmd import disable
    from nexarq_cli.cli.install_cmd import install
    from nexarq_cli.cli.review_window import open_review_window
    from nexarq_cli.cli.agent_cmd import agent
    from nexarq_cli.cli.login_cmd import login
except ImportError as _e:
    _resolve_dep(_e)   # installs + re-execs — never returns

from rich.console import Console
console = Console()

app = typer.Typer(
    name="nexarq",
    help=(
        "Nexarq CLI – multi-agent code review platform.\n\n"
        "Quick start:\n"
        "  nexarq run         Review your last commit\n"
        "  nexarq doctor      Check installation health\n"
        "  nexarq help        Full usage guide\n"
    ),
    add_completion=True,
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# ── Sub-command groups ────────────────────────────────────────────────────────
app.add_typer(config_app, name="config", help="View and modify configuration")
app.add_typer(hook_app,   name="hook",   help="Manage Git hooks")
app.add_typer(mcp_app,    name="mcp",    help="Manage MCP server integrations")

# ── Single commands ───────────────────────────────────────────────────────────
app.command("login",        help="Connect to GitHub via OAuth device flow")(login)
app.command("install",      help="One-time global setup — works in every repo after this")(install)
app.command("init",         help="Initialize Nexarq for the current project")(init)
app.command("doctor",       help="Check installation health")(doctor)
app.command("run",          help="Run the multi-agent code review pipeline")(run)
app.command("help",         help="Extended help and usage guide")(help)
app.command("enable",       help="Enable Nexarq for this repo or globally")(enable)
app.command("disable",      help="Disable Nexarq for this repo or globally")(disable)
app.command("apply",        help="Apply AI-generated fixes with approval")(apply)
app.command("coder",        help="Autonomous coding agent — plan, code, test, document")(agent)
app.command("_open_review", help="[internal] Spawn review terminal from git hook", hidden=True)(open_review_window)

# ── Version ───────────────────────────────────────────────────────────────────

def _version_callback(value: bool) -> None:
    if value:
        try:
            v = _pkg_version("nexarq-cli")
        except PackageNotFoundError:
            v = "dev"
        console.print(f"nexarq-cli {v}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Nexarq CLI – multi-agent code review."""


if __name__ == "__main__":
    app()
