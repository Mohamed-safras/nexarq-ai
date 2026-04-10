"""
Codebase context extractor — gives agents the full picture, not just the diff.

For each file changed in a diff, extracts:
  - Full current content of the changed file (so agents see the whole function, not just hunks)
  - Related test files
  - Files that import or use the changed module
  - Brief project structure summary
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexarq_cli.git.diff import DiffResult

# Max chars for a single file
_MAX_FILE_CHARS = 4000
# Max chars for a test/usage snippet
_MAX_SNIPPET_CHARS = 1500
# Total context ceiling
_MAX_TOTAL_CHARS = 10000

# Extensions that are worth reading as text
_TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
    ".rb", ".php", ".swift", ".kt", ".scala", ".cs", ".cpp", ".c", ".h",
    ".sh", ".bash", ".yaml", ".yml", ".toml", ".json", ".env.example",
    ".sql", ".graphql", ".proto",
}


def extract_context(diff_result: "DiffResult", repo_root: Path) -> str:
    """
    Build a context string for the changed files in this diff.

    Returns a formatted string ready to inject into agent system prompts.
    Returns empty string if nothing useful can be extracted.
    """
    parts: list[str] = []
    seen: set[str] = set()
    total = 0

    # ── 1. Full content of changed files ─────────────────────────────────────
    for file_path in diff_result.files[:6]:
        if total >= _MAX_TOTAL_CHARS:
            break
        abs_path = repo_root / file_path
        if not abs_path.exists() or file_path in seen:
            continue
        if abs_path.suffix not in _TEXT_EXTENSIONS:
            continue

        seen.add(file_path)
        try:
            content = abs_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if len(content) > _MAX_FILE_CHARS:
            content = content[:_MAX_FILE_CHARS] + "\n... (file truncated)"

        parts.append(f"=== CURRENT STATE: {file_path} ===\n{content}")
        total += len(content)

    # ── 2. Related test files ─────────────────────────────────────────────────
    for file_path in diff_result.files[:4]:
        if total >= _MAX_TOTAL_CHARS:
            break
        for test_path in _find_test_files(file_path, repo_root):
            if test_path in seen:
                continue
            abs_path = repo_root / test_path
            if not abs_path.exists():
                continue
            seen.add(test_path)
            try:
                content = abs_path.read_text(encoding="utf-8", errors="ignore")
                if len(content) > _MAX_SNIPPET_CHARS:
                    content = content[:_MAX_SNIPPET_CHARS] + "\n... (truncated)"
                parts.append(f"=== TEST FILE: {test_path} ===\n{content}")
                total += len(content)
            except Exception:
                pass
            break  # one test file per source file

    # ── 3. Callers / importers ────────────────────────────────────────────────
    for file_path in diff_result.files[:3]:
        if total >= _MAX_TOTAL_CHARS:
            break
        module = Path(file_path).stem
        for caller_path, snippet in _find_callers(module, repo_root, seen):
            if total >= _MAX_TOTAL_CHARS:
                break
            seen.add(caller_path)
            parts.append(f"=== CALLER: {caller_path} ===\n{snippet}")
            total += len(snippet)

    # ── 4. Project overview ───────────────────────────────────────────────────
    overview = _project_overview(repo_root)
    if overview:
        parts.insert(0, overview)

    return "\n\n".join(parts).strip()


def _find_test_files(source_path: str, repo_root: Path) -> list[str]:
    """Return paths (relative to repo root) of test files for source_path."""
    stem = Path(source_path).stem
    parent = Path(source_path).parent

    candidates = [
        f"test_{stem}.py",
        f"{stem}_test.py",
        f"{stem}.test.ts",
        f"{stem}.spec.ts",
        f"{stem}.test.js",
        f"{stem}.spec.js",
        f"test_{stem}.go",
        f"{stem}_test.go",
    ]

    found: list[str] = []
    search_dirs = [
        parent,
        parent / "tests",
        parent / "__tests__",
        Path("tests"),
        Path("test"),
        Path("spec"),
        Path("__tests__"),
    ]

    for cand in candidates:
        for d in search_dirs:
            rel = d / cand
            if (repo_root / rel).exists():
                found.append(str(rel).replace("\\", "/"))

    return found


def _find_callers(module_name: str, repo_root: Path, exclude: set[str]) -> list[tuple[str, str]]:
    """
    Use git grep to find files that import or use module_name.
    Returns list of (relative_path, snippet) pairs.
    """
    if len(module_name) < 3:  # too short, too many false positives
        return []

    patterns = [
        f"import {module_name}",
        f"from {module_name}",
        f"from .{module_name}",
        f"require('{module_name}')",
        f'require("{module_name}")',
        f"import '{module_name}'",
    ]

    found: list[tuple[str, str]] = []

    for pattern in patterns:
        try:
            r = subprocess.run(
                ["git", "grep", "-l", "--", pattern],
                capture_output=True, text=True, timeout=5,
                cwd=str(repo_root),
            )
        except Exception:
            continue

        for line in r.stdout.strip().splitlines()[:3]:
            line = line.replace("\\", "/")
            if line in exclude:
                continue
            abs_path = repo_root / line
            if not abs_path.exists():
                continue
            try:
                content = abs_path.read_text(encoding="utf-8", errors="ignore")
                snippet = _extract_snippet(content, pattern, context_lines=8, max_chars=800)
                if snippet:
                    found.append((line, snippet))
            except Exception:
                pass
            if len(found) >= 2:
                break
        if found:
            break

    return found


def _extract_snippet(content: str, pattern: str, context_lines: int, max_chars: int) -> str:
    """Extract lines around where pattern appears in content."""
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if pattern in line:
            start = max(0, i - 2)
            end = min(len(lines), i + context_lines)
            snippet = "\n".join(lines[start:end])
            return snippet[:max_chars]
    return ""


def _project_overview(repo_root: Path) -> str:
    """Return a one-paragraph project overview from git ls-files."""
    try:
        r = subprocess.run(
            ["git", "ls-files"],
            capture_output=True, text=True, timeout=5,
            cwd=str(repo_root),
        )
        files = r.stdout.strip().splitlines()
    except Exception:
        return ""

    if not files:
        return ""

    # Group by top-level directory
    dirs: dict[str, int] = {}
    for f in files:
        top = f.split("/")[0]
        dirs[top] = dirs.get(top, 0) + 1

    top_dirs = sorted(dirs.items(), key=lambda x: -x[1])[:8]
    structure = ", ".join(f"{d}/ ({n})" for d, n in top_dirs)

    # Detect project type from filenames
    all_names = set(Path(f).name for f in files)
    hints: list[str] = []
    if "pyproject.toml" in all_names or "setup.py" in all_names:
        hints.append("Python project")
    if "package.json" in all_names:
        hints.append("Node.js project")
    if "go.mod" in all_names:
        hints.append("Go module")
    if "Cargo.toml" in all_names:
        hints.append("Rust project")
    if "pom.xml" in all_names:
        hints.append("Java/Maven project")
    if "Dockerfile" in all_names:
        hints.append("containerised")
    if any(f.endswith(".tf") for f in files):
        hints.append("Terraform infra")

    project_type = " | ".join(hints) if hints else "software project"
    overview = (
        f"PROJECT OVERVIEW: {project_type} with {len(files)} tracked files. "
        f"Top-level structure: {structure}"
    )
    return f"=== PROJECT CONTEXT ===\n{overview}"
