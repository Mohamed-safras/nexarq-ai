"""
Tool definitions for the autonomous coding agent.

Each tool:
- Takes keyword arguments parsed from the LLM's tool-call block
- Returns a string result that goes back to the LLM as an Observation
- Shows diffs / command previews and asks for confirmation before any
  destructive operation (write, run command)
"""
from __future__ import annotations

import difflib
import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

_REPO_ROOT: Path = Path.cwd()


def set_repo_root(root: Path) -> None:
    global _REPO_ROOT
    _REPO_ROOT = root


def _resolve(path: str) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return (_REPO_ROOT / p).resolve()


# ── Read-only tools ────────────────────────────────────────────────────────────

def read_file(path: str = "", **_) -> str:
    if not path:
        return "ERROR: path is required"
    target = _resolve(path)
    if not target.exists():
        return f"ERROR: not found: {path}"
    if not target.is_file():
        return f"ERROR: not a file: {path}"
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"ERROR: {e}"

    lines = text.splitlines()
    numbered = "\n".join(f"{i+1:4}: {l}" for i, l in enumerate(lines[:400]))
    suffix = f"\n... ({len(lines) - 400} more lines)" if len(lines) > 400 else ""
    return f"=== {path} ({len(lines)} lines) ===\n{numbered}{suffix}"


def list_dir(path: str = ".", **_) -> str:
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
            lines.append(f"  ... ({len(items) - 100} more)")
        return f"=== {path}/ ===\n" + "\n".join(lines)
    except Exception as e:
        return f"ERROR: {e}"


def find_files(pattern: str = "**/*.py", **_) -> str:
    try:
        matches = sorted(_REPO_ROOT.glob(pattern))
        if not matches:
            return f"No files match: {pattern}"
        lines = [str(m.relative_to(_REPO_ROOT)) for m in matches[:60]]
        if len(matches) > 60:
            lines.append(f"... ({len(matches) - 60} more)")
        return "\n".join(lines)
    except Exception as e:
        return f"ERROR: {e}"


def search_code(query: str = "", file_pattern: str = "", **_) -> str:
    if not query:
        return "ERROR: query is required"

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


def git_status(**_) -> str:
    try:
        r = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, timeout=10,
            cwd=str(_REPO_ROOT),
        )
        return r.stdout.strip() or "Working tree clean."
    except Exception as e:
        return f"ERROR: {e}"


def git_diff(**_) -> str:
    try:
        r = subprocess.run(
            ["git", "diff"],
            capture_output=True, text=True, timeout=10,
            cwd=str(_REPO_ROOT),
        )
        diff = r.stdout.strip()
        if not diff:
            return "No uncommitted changes."
        if len(diff) > 4000:
            diff = diff[:4000] + "\n... (truncated)"
        return diff
    except Exception as e:
        return f"ERROR: {e}"


# ── Write tools (require confirmation) ────────────────────────────────────────

def write_file(path: str = "", content: str = "", **_) -> str:
    """Write or overwrite a file. Shows a diff and asks for confirmation."""
    if not path:
        return "ERROR: path is required"
    if not content:
        return "ERROR: content is required (provide the complete file content)"

    target = _resolve(path)

    # Read existing content for diff
    old_text = ""
    if target.exists():
        try:
            old_text = target.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # Clean trailing whitespace from content
    content = content.rstrip() + "\n"

    if old_text == content:
        return f"No changes: {path} already has this content."

    # Build unified diff
    old_lines = old_text.splitlines()
    new_lines = content.splitlines()
    diff_lines = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm="",
    ))
    diff_text = "\n".join(diff_lines)

    action = "Create" if not target.exists() else "Modify"
    console.print(
        Panel(
            Syntax(diff_text, "diff", theme="monokai", line_numbers=False),
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
        return f"Skipped: {path} not changed."

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))
        return f"Written: {path}  (+{added} -{removed} lines)"
    except Exception as e:
        return f"ERROR writing {path}: {e}"


def run_command(command: str = "", **_) -> str:
    """Run a shell command after allowlist check and user confirmation."""
    if not command:
        return "ERROR: command is required"

    _ALLOWED_PREFIXES = (
        "pytest", "python -m pytest", "python3 -m pytest",
        "npm test", "npm run test", "npx jest", "yarn test",
        "go test", "cargo test", "mvn test", "gradle test",
        "ruff check", "ruff format --check", "flake8", "pylint",
        "eslint", "prettier --check", "mypy", "pyright",
        "tsc --noEmit", "golangci-lint",
        "npm run build", "yarn build", "go build", "cargo build",
        "git status", "git log", "git diff", "git show",
    )

    stripped = command.strip()
    if not any(stripped.startswith(p) for p in _ALLOWED_PREFIXES):
        return (
            f"BLOCKED: '{stripped[:80]}' is not in the allowed command list.\n"
            "Only test runners, linters, type checkers, and read-only git commands are allowed."
        )

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
        return "Skipped: non-interactive terminal. Run the command manually."

    if ans not in ("y", "yes"):
        return "Command skipped by user."

    console.print(f"  [dim]Running: {stripped}[/dim]")
    try:
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
        return "ERROR: timed out (60s)"
    except Exception as e:
        return f"ERROR: {e}"


# ── Registry ──────────────────────────────────────────────────────────────────

TOOLS: dict[str, tuple] = {
    "read_file":   (read_file,   "Read a file with line numbers.  Params: path"),
    "write_file":  (write_file,  "Write/create a file (shows diff, asks to confirm).  Params: path, content"),
    "list_dir":    (list_dir,    "List directory contents.  Params: path (default '.')"),
    "find_files":  (find_files,  "Find files by glob pattern.  Params: pattern (e.g. '**/*.py')"),
    "search_code": (search_code, "Search for text in tracked files.  Params: query, file_pattern (optional)"),
    "run_command": (run_command, "Run a shell command (asks to confirm).  Params: command"),
    "git_status":  (git_status,  "Show current git status.  No params."),
    "git_diff":    (git_diff,    "Show current uncommitted diff.  No params."),
}


def describe_tools() -> str:
    return "\n".join(f"  {name}: {desc}" for name, (_, desc) in TOOLS.items())


def call_tool(name: str, params: dict) -> str:
    entry = TOOLS.get(name)
    if entry is None:
        available = ", ".join(TOOLS)
        return f"ERROR: unknown tool '{name}'. Available: {available}"
    fn, _ = entry
    try:
        return fn(**params)
    except Exception as e:
        return f"ERROR in {name}: {e}"


def _guess_lang(path: str) -> str:
    ext = Path(path).suffix.lstrip(".")
    return {
        "py": "python", "js": "javascript", "ts": "typescript",
        "tsx": "tsx", "jsx": "jsx", "go": "go", "rs": "rust",
        "java": "java", "rb": "ruby", "sh": "bash", "yaml": "yaml",
        "yml": "yaml", "json": "json", "toml": "toml", "md": "markdown",
        "sql": "sql", "html": "html", "css": "css",
    }.get(ext, "text")
