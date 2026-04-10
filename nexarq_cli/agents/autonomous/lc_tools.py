"""
LangChain-compatible tool definitions for the autonomous coding agent.

Each function is decorated with @tool so that LangGraph's create_react_agent
can call them via the model's tool-use interface.

Safety model (same as tools.py):
  - read_file, list_dir, find_files, search_code, git_*  → no confirmation
  - write_file, run_command                               → shows diff / command,
                                                            asks user y/n before executing
"""
from __future__ import annotations

import difflib
import subprocess
from pathlib import Path

from langchain_core.tools import tool
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

# Repo root is set once by the executor before the agent starts
_REPO_ROOT: Path = Path.cwd()


def set_repo_root(root: Path) -> None:
    global _REPO_ROOT
    _REPO_ROOT = root


def _resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (_REPO_ROOT / p).resolve()


def _guess_lang(path: str) -> str:
    return {
        "py": "python", "js": "javascript", "ts": "typescript",
        "tsx": "tsx", "go": "go", "rs": "rust", "java": "java",
        "rb": "ruby", "sh": "bash", "yaml": "yaml", "yml": "yaml",
        "json": "json", "toml": "toml", "md": "markdown", "sql": "sql",
    }.get(Path(path).suffix.lstrip("."), "text")


# ── Read-only tools ────────────────────────────────────────────────────────────

@tool
def read_file(path: str) -> str:
    """
    Read a source file and return its contents with line numbers.
    Always read a file before modifying it.
    """
    target = _resolve(path)
    if not target.exists():
        return f"ERROR: file not found: {path}"
    if not target.is_file():
        return f"ERROR: not a file: {path}"
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"ERROR reading {path}: {e}"

    lines = text.splitlines()
    numbered = "\n".join(f"{i+1:4}: {l}" for i, l in enumerate(lines[:400]))
    tail = f"\n... ({len(lines)-400} more lines)" if len(lines) > 400 else ""
    return f"=== {path} ({len(lines)} lines) ===\n{numbered}{tail}"


@tool
def list_dir(path: str = ".") -> str:
    """List the contents of a directory in the repository."""
    target = _resolve(path)
    if not target.exists():
        return f"ERROR: not found: {path}"
    try:
        items = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
        lines = []
        for item in items[:100]:
            kind = "/" if item.is_dir() else ""
            size = f"  ({item.stat().st_size:,} B)" if item.is_file() else ""
            lines.append(f"  {item.name}{kind}{size}")
        if len(items) > 100:
            lines.append(f"  ... ({len(items)-100} more)")
        return f"=== {path}/ ===\n" + "\n".join(lines)
    except Exception as e:
        return f"ERROR: {e}"


@tool
def find_files(pattern: str) -> str:
    """
    Find files by glob pattern relative to the repo root.
    Example patterns: '**/*.py', 'tests/**', 'src/*.ts'
    """
    try:
        matches = sorted(_REPO_ROOT.glob(pattern))
        if not matches:
            return f"No files match: {pattern}"
        lines = [str(m.relative_to(_REPO_ROOT)) for m in matches[:60]]
        if len(matches) > 60:
            lines.append(f"... ({len(matches)-60} more)")
        return "\n".join(lines)
    except Exception as e:
        return f"ERROR: {e}"


@tool
def search_code(query: str) -> str:
    """
    Search for a text pattern across all source files in the repository.
    Tries git grep first (fast), falls back to filesystem search for untracked files.
    Returns file:line:content matches.
    """
    results: list[str] = []

    # ── 1. git grep (tracked files) ───────────────────────────────────────
    try:
        r = subprocess.run(
            ["git", "grep", "-n", "--", query],
            capture_output=True, text=True, timeout=15,
            cwd=str(_REPO_ROOT),
        )
        if r.stdout.strip():
            results.extend(r.stdout.strip().splitlines())
    except Exception:
        pass

    # ── 2. Filesystem fallback (untracked / new files) ────────────────────
    if not results:
        _CODE_EXTS = {
            ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
            ".rb", ".php", ".swift", ".kt", ".scala", ".cs", ".cpp", ".c",
            ".sh", ".yaml", ".yml", ".toml", ".json", ".sql", ".html", ".css",
        }
        try:
            for path in sorted(_REPO_ROOT.rglob("*")):
                if path.suffix not in _CODE_EXTS or not path.is_file():
                    continue
                # Skip hidden dirs and common non-source dirs
                parts = path.relative_to(_REPO_ROOT).parts
                if any(p.startswith(".") or p in ("node_modules", "__pycache__", "dist", "build", ".git") for p in parts):
                    continue
                try:
                    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                        if query.lower() in line.lower():
                            rel = str(path.relative_to(_REPO_ROOT)).replace("\\", "/")
                            results.append(f"{rel}:{lineno}:{line.strip()}")
                            if len(results) >= 50:
                                break
                except Exception:
                    continue
                if len(results) >= 50:
                    break
        except Exception:
            pass

    if not results:
        return f"No matches for: {query}"

    output = "\n".join(results[:50])
    if len(results) > 50:
        output += f"\n... ({len(results)-50} more matches)"
    return output


@tool
def git_status() -> str:
    """Show the current git working tree status (modified, added, deleted files)."""
    try:
        r = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, timeout=10,
            cwd=str(_REPO_ROOT),
        )
        return r.stdout.strip() or "Working tree clean."
    except Exception as e:
        return f"ERROR: {e}"


@tool
def git_diff() -> str:
    """Show the current uncommitted changes as a unified diff."""
    try:
        r = subprocess.run(
            ["git", "diff"],
            capture_output=True, text=True, timeout=10,
            cwd=str(_REPO_ROOT),
        )
        diff = r.stdout.strip()
        if not diff:
            return "No uncommitted changes."
        return diff[:4000] + "\n... (truncated)" if len(diff) > 4000 else diff
    except Exception as e:
        return f"ERROR: {e}"


# ── Write tools (confirmation required) ───────────────────────────────────────

@tool
def write_file(path: str, content: str) -> str:
    """
    Write or overwrite a file with the given complete content.
    Shows a diff and asks for user confirmation before writing.
    IMPORTANT: content must be the COMPLETE file, not a partial patch.
    """
    target = _resolve(path)

    old_text = ""
    if target.exists():
        try:
            old_text = target.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass

    content = content.rstrip() + "\n"

    if old_text == content:
        return f"No changes needed — {path} already has this content."

    old_lines = old_text.splitlines()
    new_lines = content.splitlines()
    diff_lines = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{path}", tofile=f"b/{path}",
        lineterm="",
    ))
    diff_text = "\n".join(diff_lines)

    action = "Create" if not target.exists() else "Modify"
    console.print(
        Panel(
            Syntax(diff_text, "diff", theme="monokai"),
            title=f"[yellow]{action}: {path}[/yellow]",
            border_style="yellow",
            width=console.width,
        )
    )
    console.print(f"  Apply this change to [bold]{path}[/bold]? ([bold]y[/bold]/n/view): ", end="")
    try:
        ans = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "Skipped (interrupted)."

    if ans == "view":
        console.print(Syntax(content, _guess_lang(path), theme="monokai", line_numbers=True))
        console.print(f"  Apply? ([bold]y[/bold]/n): ", end="")
        try:
            ans = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "Skipped."

    if ans not in ("y", "yes", ""):
        return f"Skipped — {path} was not changed."

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))
        return f"Written: {path}  (+{added} lines  -{removed} lines)"
    except Exception as e:
        return f"ERROR writing {path}: {e}"


@tool
def run_command(command: str) -> str:
    """
    Run a shell command in the repository root (e.g. run tests, linters).
    Only safe, allowlisted command prefixes are permitted.
    Shows the full command and asks for explicit confirmation before running.
    """
    # ── Allowlist: only these command prefixes are permitted ──────────────
    # Destructive operations (rm -rf, git reset --hard, etc.) are blocked.
    _ALLOWED_PREFIXES = (
        # Test runners
        "pytest", "python -m pytest", "python3 -m pytest",
        "npm test", "npm run test", "npx jest", "yarn test",
        "go test", "cargo test", "mvn test", "gradle test",
        # Linters / formatters (read-only)
        "ruff check", "ruff format --check", "flake8", "pylint",
        "eslint", "prettier --check", "mypy", "pyright",
        "golangci-lint", "clippy", "rubocop --no-corrector",
        # Type checkers
        "tsc --noEmit", "pyright", "mypy",
        # Build (read-only check)
        "npm run build", "yarn build", "go build", "cargo build",
        "python -m build", "python3 -m build",
        # Git read-only
        "git status", "git log", "git diff", "git show",
    )

    stripped = command.strip()
    allowed = any(stripped.startswith(p) for p in _ALLOWED_PREFIXES)
    if not allowed:
        return (
            f"BLOCKED: '{stripped[:80]}' is not in the allowed command list.\n"
            "Allowed prefixes: pytest, npm test, ruff check, eslint, mypy, "
            "git status/log/diff, go test, cargo test, and similar read-only commands.\n"
            "Destructive commands (rm, git reset, git push, etc.) are never allowed."
        )

    # ── Show command and require explicit confirmation ─────────────────────
    console.print(
        Panel(
            f"[cyan]{stripped}[/cyan]",
            title="[yellow]Run command[/yellow]",
            border_style="yellow",
            width=console.width,
        )
    )
    console.print("  Execute? ([bold]y[/bold]/n): ", end="")
    try:
        ans = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        # Non-interactive terminal (git hook, CI) — never auto-approve
        return "Skipped: non-interactive terminal. Run the command manually."

    if ans not in ("y", "yes"):
        return "Command skipped by user."

    console.print("  [dim]Running…[/dim]")
    try:
        # shell=False via list split — safer than shell=True
        import shlex
        args = shlex.split(stripped)
        r = subprocess.run(
            args,
            capture_output=True, text=True,
            timeout=60, cwd=str(_REPO_ROOT),
        )
        output = (r.stdout + r.stderr).strip()
        if len(output) > 4000:
            output = output[:4000] + "\n... (truncated)"
        status = "SUCCESS" if r.returncode == 0 else f"FAILED (exit {r.returncode})"
        return f"{status}\n{output}" if output else status
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out (60 s)"
    except Exception as e:
        return f"ERROR: {e}"


# ── Review agents as tools ────────────────────────────────────────────────────
# Wraps every agent registered in REGISTRY as a callable LangChain tool.
# This lets nexarq coder use the same agents as nexarq run — after writing code
# it can call review_code(agent="security") to check its own changes.

@tool
def review_code(agent: str, code: str, language: str = "auto") -> str:
    """
    Run a nexarq review agent against a code snippet or file contents.

    agent    — name of the agent to run. Common choices:
               security, bugs, performance, type_safety, error_handling,
               code_smells, maintainability, test_coverage, secrets_detection
    code     — the code to review (paste contents or a diff)
    language — programming language hint (auto-detected if omitted)

    Returns the agent's findings as plain text.
    Use this after writing or editing code to verify your changes are correct.
    """
    try:
        from nexarq_cli.agents.registry import REGISTRY
        from nexarq_cli.config.manager import ConfigManager
        from nexarq_cli.llm.factory import LLMFactory
        from nexarq_cli.security.secrets import SecretsManager

        cfg = ConfigManager().load()
        factory = LLMFactory(cfg, SecretsManager())

        try:
            ag = REGISTRY.get(agent)
        except KeyError:
            available = ", ".join(REGISTRY.names())
            return f"Unknown agent '{agent}'. Available: {available}"

        lang = language if language != "auto" else "unknown"

        from nexarq_cli.frameworks.lc_llm import get_lc_llm
        lc_llm = get_lc_llm(cfg)
        result = ag.run_lc(code, lang, lc_llm, {})

        if result.error:
            return f"Agent error: {result.error}"

        sev = result.severity.value if hasattr(result.severity, "value") else str(result.severity)
        header = f"[{sev.upper()}] {agent.upper()} findings:\n"
        return header + (result.output or "No issues found.")

    except Exception as exc:
        return f"ERROR running agent '{agent}': {exc}"


@tool
def list_review_agents() -> str:
    """
    List all available nexarq review agents and their descriptions.
    Use this to discover which agents you can pass to review_code().
    """
    try:
        from nexarq_cli.agents.registry import REGISTRY
        lines = []
        for name, desc in sorted(REGISTRY.descriptions().items()):
            lines.append(f"  {name:<22} {desc}")
        return "\n".join(lines)
    except Exception as exc:
        return f"ERROR: {exc}"


# ── Tool list exported for create_react_agent ──────────────────────────────────

ALL_TOOLS = [
    read_file,
    write_file,
    list_dir,
    find_files,
    search_code,
    run_command,
    git_status,
    git_diff,
    review_code,
    list_review_agents,
]
