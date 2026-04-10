"""
RAG retriever — public API for extracting codebase context.

Usage:
    retriever = ContextRetriever(repo_root)
    context_str = retriever.retrieve(diff_result)
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexarq_cli.git.diff import DiffResult


class ContextRetriever:
    """
    Retrieve codebase context relevant to a code diff.

    Extracts the full current content of changed files so agents can see
    the complete picture — not just the lines that changed.
    """

    def __init__(self, repo_root: Path | str | None = None) -> None:
        self._repo_root = self._resolve_root(repo_root)

    def retrieve(self, diff_result: "DiffResult") -> str:
        """
        Return a formatted codebase context string for the given diff.
        Empty string if repo root cannot be determined or no context found.
        """
        if self._repo_root is None:
            return ""
        try:
            from nexarq_cli.rag.context import extract_context
            return extract_context(diff_result, self._repo_root)
        except Exception:
            return ""

    # ── internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_root(root: Path | str | None) -> Path | None:
        """Resolve repo root from argument, GIT_DIR env var, or git command."""
        import os
        import subprocess

        if root is not None:
            return Path(root).resolve()

        # Use GIT_DIR if set by git hook
        gd = os.environ.get("GIT_DIR")
        if gd:
            gd_path = Path(gd)
            candidate = gd_path.parent if gd_path.name == ".git" else gd_path
            if candidate.exists():
                return candidate.resolve()

        # Fall back to git command
        try:
            r = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                return Path(r.stdout.strip()).resolve()
        except Exception:
            pass

        return None
