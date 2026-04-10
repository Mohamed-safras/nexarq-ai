"""
Internal: smart review launcher for post-commit hook.

Called synchronously by the post-commit hook:
    python -m nexarq_cli _open_review

Behaviour — platform-independent TTY detection:

  Already in a terminal (CLI commit, VS Code integrated terminal)
    → review runs inline in the SAME terminal, no new window opened

  No terminal attached (VS Code Source Control panel, any GUI-based commit)
    → opens a new terminal window using the system default
       (Windows Terminal, cmd, macOS Terminal, gnome-terminal, etc.)
       at the repo directory of the committed project
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def open_review_window() -> None:
    """
    Inline if a terminal is already open, new window if headless.

    "Already open" includes:
      - Any shell terminal (PowerShell, bash, zsh, cmd…)
      - VS Code integrated terminal
      - JetBrains embedded terminal
      - Windows Terminal, iTerm2, Alacritty, etc.

    Detection is TTY-based — platform and editor independent.
    """
    python = sys.executable
    cwd    = _get_repo_root()
    cmd    = [python, "-m", "nexarq_cli", "run", "--hook", "post-commit"]

    if _has_terminal():
        # ── Terminal already open: run review right here ──────────────────
        # os.execv replaces this process in the same session — no new window.
        os.chdir(str(cwd))
        os.execv(python, cmd)
        # never returns

    # ── Headless (IDE GUI commit): open a new terminal window ─────────────
    _open_new_terminal(cmd, cwd)


def _has_terminal() -> bool:
    """
    Return True if a real interactive terminal is attached.

    Catches both plain TTY sessions AND IDE embedded terminals
    (VS Code terminal, JetBrains terminal, etc.) which all have
    a real TTY but may or may not set TERM_PROGRAM.
    """
    # Primary: standard POSIX TTY check — works for every terminal type
    if sys.stdin.isatty() and sys.stdout.isatty():
        return True

    # Secondary: well-known editor terminal env vars (some IDEs don't set TTY
    # on their embedded terminals in edge cases)
    editor_markers = [
        os.environ.get("TERM_PROGRAM"),           # vscode, iTerm.app, …
        os.environ.get("TERMINAL_EMULATOR"),       # JetBrains-JediTerm
        os.environ.get("IDEA_INITIAL_DIRECTORY"),  # JetBrains
        os.environ.get("VSCODE_GIT_ASKPASS_NODE"), # VS Code terminal
        os.environ.get("WT_SESSION"),              # Windows Terminal
    ]
    return any(v for v in editor_markers if v)


def _open_new_terminal(cmd: list[str], cwd: Path) -> None:
    """
    Open a new terminal window using whatever is installed on the system.
    Never hardcodes a specific terminal emulator.
    """
    if sys.platform == "win32":
        _open_windows(cmd, cwd)
    elif sys.platform == "darwin":
        _open_macos(cmd, cwd)
    else:
        _open_linux(cmd, cwd)


# ── Windows ───────────────────────────────────────────────────────────────────

def _open_windows(cmd: list[str], cwd: Path) -> None:
    """
    Use 'cmd /c start' — opens in the system's default terminal.
    On Windows 11 this respects the user's default terminal setting
    (Windows Terminal, ConHost, etc.) without hardcoding any specific shell.
    'start' uses ShellExecuteEx internally, which works even when the parent
    process has no desktop session (VS Code's headless git context).
    """
    cwd_str = str(cwd)

    # Write a tiny .bat that changes to the right dir and runs nexarq
    # Using a .bat avoids all argument-quoting issues with 'start'.
    import tempfile, atexit

    bat = tempfile.NamedTemporaryFile(
        mode="w", suffix=".bat", delete=False, encoding="utf-8"
    )
    bat.write("@echo off\n")
    bat.write("chcp 65001 > nul\n")       # UTF-8 so review text renders correctly
    bat.write(f'cd /d "{cwd_str}"\n')
    bat.write(f'"{cmd[0]}" {" ".join(cmd[1:])}\n')
    # No 'pause' here — Python prints its own "press Enter to close" message
    # and waits, so the window doesn't snap closed before the user reads it.
    bat.close()

    # 'start' opens the .bat in the system default terminal (non-blocking)
    subprocess.Popen(
        ["cmd", "/c", "start", "Nexarq Review", bat.name],
        creationflags=subprocess.CREATE_NO_WINDOW,
        cwd=cwd_str,
    )

    # Clean up after a delay — give the terminal enough time to load the file
    # (atexit fires when this Python process exits, ~immediately after Popen)
    import threading
    threading.Timer(5.0, _safe_delete, args=[bat.name]).start()


# ── macOS ─────────────────────────────────────────────────────────────────────

def _open_macos(cmd: list[str], cwd: Path) -> None:
    """Open a new Terminal.app window on macOS."""
    inner = " ".join(f'"{c}"' if " " in c else c for c in cmd)
    apple_script = (
        f'tell application "Terminal"\n'
        f'  do script "cd {shq(str(cwd))} && {inner}"\n'
        f'  activate\n'
        f'end tell'
    )
    subprocess.Popen(["osascript", "-e", apple_script])


# ── Linux ─────────────────────────────────────────────────────────────────────

def _open_linux(cmd: list[str], cwd: Path) -> None:
    """Try common terminal emulators in order of preference."""
    attempts = [
        ["gnome-terminal", "--working-directory", str(cwd), "--"] + cmd,
        ["kitty", "--directory", str(cwd)] + cmd,
        ["alacritty", "--working-directory", str(cwd), "-e"] + cmd,
        ["konsole", "--workdir", str(cwd), "-e"] + cmd,
        ["xfce4-terminal", "--working-directory", str(cwd), "-x"] + cmd,
        ["xterm", "-e"] + cmd,
    ]
    for attempt in attempts:
        try:
            subprocess.Popen(attempt, cwd=str(cwd))
            return
        except FileNotFoundError:
            continue
    # Last resort: detached subprocess (visible if parent has a terminal)
    subprocess.Popen(cmd, cwd=str(cwd), start_new_session=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def shq(s: str) -> str:
    """Shell-quote a string for use in AppleScript / bash."""
    return "'" + s.replace("'", "'\\''") + "'"


def _safe_delete(path: str) -> None:
    try:
        os.unlink(path)
    except Exception:
        pass


def _get_repo_root() -> Path:
    """
    Resolve the work tree of the repo being committed to.
    Git sets GIT_DIR when running hooks — its parent is always the work tree.
    """
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

    return Path.cwd().resolve()
