"""
Git hook installer – embeds absolute Python path so hooks work without
activating any conda/venv environment first.

Key design: at install time, sys.executable is captured and written directly
into the hook script, so git can always invoke Nexarq regardless of PATH.
"""
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path
from string import Template


# ── Hook templates ────────────────────────────────────────────────────────────
# $PYTHON  – absolute path to the Python interpreter (substituted at install)
# $APP_DIR – absolute path to the nexarq-cli package directory (substituted at install)

_POST_COMMIT_TEMPLATE = """\
#!/bin/sh
# Nexarq post-commit hook
# Auto-installed by Nexarq CLI. To remove: nexarq hook uninstall post-commit
#
# Opens a new terminal window with the interactive review + approval flow.
# The commit itself is NEVER blocked — this hook always exits 0.
# Bypass: NEXARQ_SKIP=1 git commit

NEXARQ_PYTHON="NEXARQ_PY_PATH"

if [ "${NEXARQ_SKIP}" = "1" ]; then
  exit 0
fi

if [ ! -f "$NEXARQ_PYTHON" ]; then
  echo "[nexarq] Python not found at $NEXARQ_PYTHON — skipping review"
  exit 0
fi

# Smart launcher:
#   - already in a terminal → runs review inline in this session
#   - headless (VS Code GUI, IDE button) → opens system default terminal
# Non-blocking in both cases: inline path uses os.execv (replaces process),
# new-window path returns immediately after spawning.
"$NEXARQ_PYTHON" -m nexarq_cli _open_review
exit 0
"""

_COMMIT_MSG_TEMPLATE = """\
#!/bin/sh
# Nexarq commit-msg hook
# Auto-installed by Nexarq CLI. To remove: nexarq hook uninstall commit-msg
#
# Validates commit message format (optional – exits 0 if no validator configured).

NEXARQ_PYTHON="NEXARQ_PY_PATH"
COMMIT_MSG_FILE="$1"

if [ "${NEXARQ_SKIP}" = "1" ]; then
  exit 0
fi

# Allow commit if Python not found (never block development)
if [ ! -f "$NEXARQ_PYTHON" ]; then
  exit 0
fi

# Validate: run only if a validator is configured, otherwise always pass
"$NEXARQ_PYTHON" -m nexarq_cli run --hook commit-msg --no-interactive > /dev/null 2>&1 || true
exit 0
"""

_PRE_PUSH_TEMPLATE = """\
#!/bin/sh
# Nexarq pre-push hook
# Auto-installed by Nexarq CLI. To remove: nexarq hook uninstall pre-push
#
# Runs code review synchronously before every push.
# Blocks the push if CRITICAL/HIGH issues are found.
# Bypass: NEXARQ_SKIP=1 git push

NEXARQ_PYTHON="NEXARQ_PY_PATH"

if [ "${NEXARQ_SKIP}" = "1" ]; then
  echo "[nexarq] Hook bypassed via NEXARQ_SKIP=1"
  exit 0
fi

if [ ! -f "$NEXARQ_PYTHON" ]; then
  echo "[nexarq] Python not found at $NEXARQ_PYTHON — push allowed without review"
  exit 0
fi

echo "[nexarq] Running pre-push code review..."
"$NEXARQ_PYTHON" -m nexarq_cli run --hook pre-push --no-interactive
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo ""
  echo "[nexarq] Push blocked: critical issues detected."
  echo "[nexarq] Fix the issues or bypass with: NEXARQ_SKIP=1 git push"
  exit 1
fi

exit 0
"""


class HookInstaller:
    """
    Installs Nexarq Git hooks with absolute Python path embedded.

    The installed hook script never relies on PATH or conda activation —
    it calls the exact Python interpreter that installed Nexarq.
    """

    def __init__(self, repo_path: str | Path = ".") -> None:
        try:
            import git
            repo = git.Repo(repo_path, search_parent_directories=True)
            self.hooks_dir = Path(repo.git_dir) / "hooks"
        except Exception:
            self.hooks_dir = Path(repo_path) / ".git" / "hooks"

    # ── public ───────────────────────────────────────────────────────────────

    def install(self, hook_type: str = "post-commit") -> Path:
        """
        Install a hook script with the current Python interpreter embedded.

        Never blocks an existing hook — backs it up first.
        """
        self.hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_path = self.hooks_dir / hook_type

        # Resolve Python and package paths at install time
        python_exe = self._find_python()
        app_dir = self._app_dir()

        script = self._render(hook_type, python_exe, app_dir)

        # Back up any existing hook that isn't ours
        if hook_path.exists():
            content = hook_path.read_text(encoding="utf-8", errors="ignore")
            if "Nexarq" not in content:
                backup = hook_path.with_suffix(".nexarq-backup")
                hook_path.rename(backup)

        hook_path.write_text(script, encoding="utf-8")
        self._make_executable(hook_path)
        return hook_path

    def uninstall(self, hook_type: str = "post-commit") -> bool:
        """Remove Nexarq hook; restore backup if present."""
        hook_path = self.hooks_dir / hook_type
        backup = hook_path.with_suffix(".nexarq-backup")

        if not hook_path.exists():
            return False

        content = hook_path.read_text(encoding="utf-8", errors="ignore")
        if "Nexarq" not in content:
            return False  # Not our hook, don't touch it

        hook_path.unlink()

        if backup.exists():
            backup.rename(hook_path)

        return True

    def status(self) -> dict[str, str]:
        """Return installation status for each hook type."""
        result = {}
        for htype in ("post-commit", "pre-push"):
            hp = self.hooks_dir / htype
            if hp.exists():
                content = hp.read_text(encoding="utf-8", errors="ignore")
                result[htype] = "nexarq" if "Nexarq" in content else "other"
            else:
                result[htype] = "not installed"
        return result

    def python_path(self) -> str:
        """Return the Python path that would be embedded in hooks."""
        return self._find_python()

    # ── internal ─────────────────────────────────────────────────────────────

    def _render(self, hook_type: str, python_exe: str, app_dir: str) -> str:
        templates = {
            "post-commit": _POST_COMMIT_TEMPLATE,
            "pre-push": _PRE_PUSH_TEMPLATE,
            "commit-msg": _COMMIT_MSG_TEMPLATE,
        }
        tmpl = templates.get(hook_type)
        if tmpl is None:
            raise ValueError(f"Unsupported hook type: {hook_type!r}")

        # Use a unique placeholder to avoid conflicts with shell $VAR syntax
        return tmpl.replace("NEXARQ_PY_PATH", python_exe)

    def _find_python(self) -> str:
        """
        Return the absolute path to the Python interpreter to embed in hooks.

        Priority:
          1. sys.executable (the interpreter running Nexarq right now — always correct)
          2. nexarq script next to sys.executable (for pip-installed entry point)
          3. Fallback: 'python' (will warn at commit time if missing)
        """
        # sys.executable is always the conda/venv Python that runs this code
        exe = Path(sys.executable)
        if exe.exists():
            # On Windows, convert to forward slashes for sh compatibility
            return exe.as_posix()

        # Search common locations
        for candidate in ["python3", "python"]:
            found = _which(candidate)
            if found:
                return found

        return "python"

    def _app_dir(self) -> str:
        """Return the absolute path to the app package directory."""
        here = Path(__file__).parent.parent  # nexarq-cli/nexarq_cli/git/hooks.py → nexarq-cli
        return here.as_posix()

    @staticmethod
    def _make_executable(path: Path) -> None:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def _which(cmd: str) -> str:
    """Cross-platform which."""
    import shutil
    found = shutil.which(cmd)
    return Path(found).as_posix() if found else ""
