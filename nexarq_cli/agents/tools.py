"""
Read-only review tools for tool-augmented Nexarq agents.

Security model:
  - All paths resolved strictly inside _REPO_ROOT — no traversal (SEC-PATH-1)
  - All tool outputs redacted before returning to the LLM (SEC-REDACT-1)
  - No writes, no shell execution, no network access (SEC-7/8/9)
  - Output size capped to prevent prompt-stuffing (SEC-OUT-1)
  - Symlinks followed only if target is still inside repo root (SEC-PATH-2)
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from langchain_core.tools import tool

# ── Repo root (set once per run by make_review_tools) ─────────────────────────

_REPO_ROOT: Path = Path.cwd().resolve()

# Patterns redacted from all tool outputs before returning to the LLM
_REDACT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(
        r'(?i)(api[_\-]?key|secret[_\-]?key|access[_\-]?token|auth[_\-]?token'
        r'|password|passwd|credential|private[_\-]?key)\s*[=:]\s*["\']?[\w\-./+]{8,}["\']?'
    ), "<REDACTED_CREDENTIAL>"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*"), "bearer <REDACTED_TOKEN>"),
    (re.compile(r"(?i)(AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}"), "<REDACTED_AWS_KEY>"),
    (re.compile(
        r"-----BEGIN\s+[\w ]+PRIVATE KEY-----[\s\S]*?-----END\s+[\w ]+PRIVATE KEY-----"
    ), "<REDACTED_PRIVATE_KEY>"),
    (re.compile(r'(?<=["\' =])[A-Za-z0-9+/]{40,}={0,2}(?=["\' \n])'), "<REDACTED_SECRET>"),
    (re.compile(
        r"(?i)(postgres|mysql|mongodb|redis|amqp)://[^:]+:[^@]+@"
    ), r"\1://<REDACTED>@"),
]

# Extensions allowed to be read (no binaries, no key files)
_ALLOWED_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
    ".rb", ".php", ".swift", ".kt", ".scala", ".cs", ".cpp", ".c", ".h",
    ".sh", ".bash", ".yaml", ".yml", ".toml", ".json", ".env.example",
    ".sql", ".graphql", ".proto", ".md", ".txt", ".html", ".css",
    ".tf", ".hcl", ".dockerfile", ".xml", ".ini", ".cfg",
}

# Filenames that must never be read regardless of extension
_BLOCKED_FILENAMES = {
    ".env", ".env.local", ".env.production", ".env.staging",
    "secrets.yaml", "secrets.yml", "credentials.json",
    "serviceaccount.json", "keystore.jks", "truststore.jks",
    ".netrc", ".npmrc", ".pypirc",
}

_MAX_FILE_CHARS = 8_000
_MAX_OUTPUT_CHARS = 6_000


def set_review_repo_root(root: Path | str | None) -> None:
    global _REPO_ROOT
    if root:
        _REPO_ROOT = Path(root).resolve()


def _safe_resolve(path: str) -> Path | None:
    """
    Resolve a path strictly inside the repo root.

    Returns None (access denied) if:
      - the resolved path escapes the repo root (path traversal)
      - the resolved path is a blocked filename
      - the symlink target escapes the repo root
    """
    try:
        p = Path(path)
        if p.is_absolute():
            resolved = p.resolve()
        else:
            resolved = (_REPO_ROOT / p).resolve()

        # SEC-PATH-1: must be inside repo root
        resolved.relative_to(_REPO_ROOT)

        # SEC-PATH-2: follow symlinks and re-check
        if resolved.is_symlink():
            real = resolved.readlink() if hasattr(resolved, "readlink") else Path(
                __import__("os").readlink(resolved)
            )
            if not real.is_absolute():
                real = (resolved.parent / real).resolve()
            real.relative_to(_REPO_ROOT)

        # SEC-FNAME: blocked filenames
        if resolved.name in _BLOCKED_FILENAMES:
            return None

        return resolved

    except (ValueError, Exception):
        return None


def _redact(text: str) -> str:
    """Strip secrets from tool output before it reaches the LLM."""
    for pattern, replacement in _REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _cap(text: str, max_chars: int = _MAX_OUTPUT_CHARS) -> str:
    if len(text) > max_chars:
        return text[:max_chars] + f"\n... [truncated at {max_chars} chars]"
    return text


def _safe_output(text: str) -> str:
    """Redact + cap every tool output."""
    return _cap(_redact(text))


# ── Tools ──────────────────────────────────────────────────────────────────────

@tool
def read_file(path: str) -> str:
    """
    Read a source file with line numbers.
    Path is relative to the repository root.
    Blocked: .env, credentials, private keys, binary files.
    """
    target = _safe_resolve(path)
    if target is None:
        return f"ACCESS DENIED: '{path}' is outside the repository or is a sensitive file."
    if not target.exists():
        return f"NOT FOUND: {path}"
    if not target.is_file():
        return f"NOT A FILE: {path}"

    # Extension check — no binary or key files
    if target.suffix and target.suffix.lower() not in _ALLOWED_EXTENSIONS:
        return f"BLOCKED: extension '{target.suffix}' is not readable by review agents."

    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"ERROR reading {path}: {e}"

    if len(text) > _MAX_FILE_CHARS:
        text = text[:_MAX_FILE_CHARS] + f"\n... [file truncated at {_MAX_FILE_CHARS} chars]"

    lines = text.splitlines()
    numbered = "\n".join(f"{i+1:4}: {ln}" for i, ln in enumerate(lines))
    return _safe_output(f"=== {path} ===\n{numbered}")


@tool
def search_code(query: str) -> str:
    """
    Search for a text pattern across all tracked source files.
    Returns file:line:content matches (max 40 results).
    Use to find where a function is called, imported, or a pattern exists.
    """
    if not query or len(query.strip()) < 2:
        return "ERROR: query must be at least 2 characters."
    if len(query) > 200:
        return "ERROR: query too long (max 200 chars)."

    results: list[str] = []

    try:
        r = subprocess.run(
            ["git", "grep", "-n", "--max-count=3", "--", query],
            capture_output=True, text=True, timeout=10,
            cwd=str(_REPO_ROOT),
        )
        if r.stdout.strip():
            results.extend(r.stdout.strip().splitlines())
    except Exception:
        pass

    # Filesystem fallback (untracked files)
    if not results:
        try:
            for fpath in sorted(_REPO_ROOT.rglob("*")):
                if not fpath.is_file():
                    continue
                if fpath.suffix.lower() not in _ALLOWED_EXTENSIONS:
                    continue
                if fpath.name in _BLOCKED_FILENAMES:
                    continue
                parts = fpath.relative_to(_REPO_ROOT).parts
                if any(p.startswith(".") or p in (
                    "node_modules", "__pycache__", "dist", "build", ".git"
                ) for p in parts):
                    continue
                try:
                    for lineno, line in enumerate(
                        fpath.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
                    ):
                        if query.lower() in line.lower():
                            rel = str(fpath.relative_to(_REPO_ROOT)).replace("\\", "/")
                            results.append(f"{rel}:{lineno}:{line.strip()}")
                            if len(results) >= 40:
                                break
                except Exception:
                    pass
                if len(results) >= 40:
                    break
        except Exception:
            pass

    if not results:
        return f"No matches found for: {query!r}"

    return _safe_output("\n".join(results[:40]))


@tool
def find_references(symbol: str) -> str:
    """
    Find all references to a function, class, or variable name (word-boundary match).
    symbol: exact identifier, e.g. 'authenticate', 'UserModel', 'DB_PASSWORD'
    """
    if not symbol or len(symbol.strip()) < 2:
        return "ERROR: symbol must be at least 2 characters."
    if not re.match(r'^[\w\.\-]+$', symbol):
        return "ERROR: symbol contains invalid characters."

    try:
        r = subprocess.run(
            ["git", "grep", "-n", "--word-regexp", "--", symbol],
            capture_output=True, text=True, timeout=10,
            cwd=str(_REPO_ROOT),
        )
        lines = r.stdout.strip().splitlines()
    except Exception as e:
        return f"ERROR: {e}"

    if not lines:
        return f"No references found for: {symbol!r}"

    return _safe_output("\n".join(lines[:50]))


@tool
def list_directory(path: str = ".") -> str:
    """
    List files and subdirectories at the given path (relative to repo root).
    Does not show hidden directories or node_modules.
    """
    target = _safe_resolve(path)
    if target is None:
        return f"ACCESS DENIED: '{path}'"
    if not target.exists():
        return f"NOT FOUND: {path}"
    if not target.is_dir():
        return f"NOT A DIRECTORY: {path}"

    try:
        items = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
        lines = []
        for item in items[:80]:
            if item.name.startswith(".") or item.name in (
                "node_modules", "__pycache__", ".git"
            ):
                continue
            kind = "/" if item.is_dir() else ""
            size = f"  {item.stat().st_size:,}B" if item.is_file() else ""
            lines.append(f"  {item.name}{kind}{size}")
        if len(items) > 80:
            lines.append(f"  ... ({len(items) - 80} more)")
        return _safe_output(f"=== {path}/ ===\n" + "\n".join(lines))
    except Exception as e:
        return f"ERROR: {e}"


@tool
def get_git_log(file_path: str = "", limit: int = 5) -> str:
    """
    Get recent git commit history for a file or the whole repo.
    file_path: relative path, or empty for repo-wide log.
    limit: 1–10 commits.
    """
    limit = max(1, min(int(limit), 10))

    # Validate file_path if given
    if file_path:
        target = _safe_resolve(file_path)
        if target is None:
            return f"ACCESS DENIED: '{file_path}'"
        file_path = str(target.relative_to(_REPO_ROOT)).replace("\\", "/")

    cmd = ["git", "log", f"--max-count={limit}", "--oneline"]
    if file_path:
        cmd += ["--", file_path]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
            cwd=str(_REPO_ROOT),
        )
        return _safe_output(r.stdout.strip() or "No commits found.")
    except Exception as e:
        return f"ERROR: {e}"


# ── Exported tool list ─────────────────────────────────────────────────────────

REVIEW_TOOLS = [
    read_file,
    search_code,
    find_references,
    list_directory,
    get_git_log,
]


def make_review_tools(repo_root: str | None = None) -> list:
    """
    Return scoped read-only tools. Called once per run_agentic() invocation.
    """
    set_review_repo_root(repo_root)
    return REVIEW_TOOLS
