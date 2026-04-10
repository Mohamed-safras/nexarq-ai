"""
nexarq login — GitHub OAuth device flow.

Screen 1  (splash):
  [NEXARQ banner]
  Press ENTER to login with GitHub...

Screen 2  (waiting for browser):
  [NEXARQ banner]
  Open this URL in your browser to login:
  https://github.com/login/device?user_code=XXXX-XXXX
  [ Copy link (c) ]
  Waiting for login...

Screen 3  (success):
  [NEXARQ banner]
  ✓  Logged in as @username
  nexarq is ready.
"""
from __future__ import annotations

import sys
import threading
import time

import typer
from rich.console import Console
from rich.text import Text

console = Console()


# ── Shared banner renderer ────────────────────────────────────────────────────

def _print_banner() -> None:
    """Clear screen and print the NEXARQ block-art banner."""
    console.clear()
    console.print()
    console.print()

    B = "\u2588"  # █ full block
    lines = [
        f"  {B}{B}{B}{B}   {B}{B} {B}{B}{B}{B}{B}  {B}{B}  {B}{B}  {B}{B}{B}{B}{B}  {B}{B}{B}{B}{B}{B}{B}   {B}{B}{B}{B}{B} ",
        f"  {B}{B}{B}{B}{B}  {B}{B} {B}{B}      {B}{B}{B} {B}{B}{B} {B}{B}   {B}{B} {B}{B}   {B}{B}   {B}{B}   {B}{B}",
        f"  {B}{B} {B}{B} {B}{B} {B}{B}{B}{B}{B}   {B}{B}{B}{B}{B}{B}  {B}{B}{B}{B}{B}{B}{B} {B}{B}{B}{B}{B}{B}{B}   {B}{B}   {B}{B}",
        f"  {B}{B}  {B}{B}{B}{B} {B}{B}      {B}{B} {B}{B}{B} {B}{B} {B}{B}   {B}{B} {B}{B}  {B}{B}   {B}{B} {B}{B}{B}{B}{B}",
        f"  {B}{B}   {B}{B}{B} {B}{B}{B}{B}{B}  {B}{B}   {B}{B} {B}{B}   {B}{B} {B}{B}   {B}{B} {B}{B}{B}{B}{B}  {B}{B}{B}{B} ",
    ]
    for line in lines:
        console.print(line, style="cyan", highlight=False)

    console.print()


# ── Clipboard helper ──────────────────────────────────────────────────────────

def _copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard. Returns True on success."""
    import subprocess, sys as _sys
    try:
        if _sys.platform == "win32":
            subprocess.run("clip", input=text.encode("utf-8"),
                           check=True, capture_output=True)
        elif _sys.platform == "darwin":
            subprocess.run("pbcopy", input=text.encode("utf-8"),
                           check=True, capture_output=True)
        else:
            # Linux — try xclip, xsel, wl-copy in order
            for cmd in (["xclip", "-selection", "clipboard"],
                        ["xsel", "--clipboard", "--input"],
                        ["wl-copy"]):
                try:
                    subprocess.run(cmd, input=text.encode("utf-8"),
                                   check=True, capture_output=True)
                    return True
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue
            return False
        return True
    except Exception:
        return False


# ── Animated "Waiting for login..." ticker ────────────────────────────────────

_DOTS = ["   ", ".  ", ".. ", "..."]


class _WaitingTicker:
    """Prints an animated 'Waiting for login...' line in-place."""

    def __init__(self) -> None:
        self._i = 0
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._t.start()

    def stop(self) -> None:
        self._stop.set()
        self._t.join(timeout=1)
        # Erase the line
        sys.stdout.write("\r" + " " * 40 + "\r")
        sys.stdout.flush()

    def _run(self) -> None:
        while not self._stop.is_set():
            dots = _DOTS[self._i % len(_DOTS)]
            sys.stdout.write(f"\r  [dim]Waiting for login{dots}[/dim]")
            sys.stdout.flush()
            self._i += 1
            time.sleep(0.4)


# ── Main command ──────────────────────────────────────────────────────────────

def login(
    client_id: str = typer.Option(
        "", "--client-id",
        help="GitHub OAuth App client ID (overrides NEXARQ_GITHUB_CLIENT_ID)",
        envvar="NEXARQ_GITHUB_CLIENT_ID",
    ),
    logout: bool = typer.Option(False, "--logout", help="Log out and remove stored token"),
) -> None:
    """
    Connect nexarq to your GitHub account via OAuth device flow.

    Opens a browser-based login — no password is ever entered in the terminal.
    """
    from nexarq_cli.auth.github import GitHubAuth
    from nexarq_cli.auth.token import TokenStore

    # ── Logout ────────────────────────────────────────────────────────────────
    if logout:
        _print_banner()
        stored = TokenStore.load()
        if stored:
            TokenStore.clear()
            console.print(f"  [green]✓[/green]  Logged out ({stored.get('username', '')})")
        else:
            console.print("  Not logged in.")
        console.print()
        raise typer.Exit(0)

    # ── Already logged in? ────────────────────────────────────────────────────
    existing = TokenStore.load()
    if existing:
        _print_banner()
        uname = existing.get("username", "unknown")
        console.print(f"  [green]✓[/green]  Already logged in as [bold cyan]@{uname}[/bold cyan]")
        console.print()
        console.print("  [dim]To switch accounts run:[/dim]  nexarq login --logout")
        console.print()
        raise typer.Exit(0)

    # ── Screen 1: splash ──────────────────────────────────────────────────────
    _print_banner()

    console.print(
        "  [dim]Connect nexarq to GitHub for private-repo context and account tracking.[/dim]"
    )
    console.print()
    console.print(
        "  [bold white]Press ENTER to login with GitHub[/bold white]"
        " [dim](or q to skip)[/dim]  ",
        end="",
    )

    try:
        ans = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print("\n  [yellow]Skipped.[/yellow]")
        raise typer.Exit(0)

    if ans in ("q", "quit", "skip", "n", "no"):
        console.print("\n  [yellow]Skipped.[/yellow]  Run [cyan]nexarq login[/cyan] any time.")
        console.print()
        raise typer.Exit(0)

    # ── Request device code ───────────────────────────────────────────────────
    _print_banner()
    console.print("  [dim]Connecting to GitHub…[/dim]")
    console.print()

    try:
        auth = GitHubAuth(client_id=client_id)
        dc = auth.request_device_code()
    except RuntimeError as exc:
        console.print(f"  [red]Error:[/red] {exc}")
        console.print()
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"  [red]Could not reach GitHub:[/red] {exc}")
        console.print()
        raise typer.Exit(1)

    # ── Screen 2: show URL ────────────────────────────────────────────────────
    _print_banner()

    auth_url = dc.verification_uri_complete

    console.print("  Open this URL in your browser to login:")
    console.print()
    console.print(f"  [bold cyan]{auth_url}[/bold cyan]")
    console.print()
    console.print("  [dim][ Copy link ([bold]c[/bold]) ][/dim]  ", end="", flush=True)

    # Non-blocking: read a key without waiting (stdin check)
    try:
        import select, tty, termios
        old = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())
        r, _, _ = select.select([sys.stdin], [], [], 0.1)
        if r:
            ch = sys.stdin.read(1).lower()
            if ch == "c":
                ok = _copy_to_clipboard(auth_url)
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
                if ok:
                    console.print("\r  [green]✓[/green]  Link copied to clipboard                    ")
                else:
                    console.print("\r  [yellow]![/yellow]  Could not copy — paste the URL manually    ")
            else:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
        else:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
    except Exception:
        # Windows / non-tty: offer y/n copy prompt after a newline
        try:
            line = input().strip().lower()
            if line == "c":
                ok = _copy_to_clipboard(auth_url)
                if ok:
                    console.print("  [green]✓[/green]  Link copied to clipboard")
                else:
                    console.print("  [yellow]![/yellow]  Could not copy — paste the URL manually")
        except (EOFError, KeyboardInterrupt):
            pass

    console.print()
    console.print()

    # ── Poll with animated ticker ─────────────────────────────────────────────
    ticker = _WaitingTicker()
    ticker.start()

    try:
        result = auth.poll_for_token(dc)
    except KeyboardInterrupt:
        ticker.stop()
        console.print("\n  [yellow]Cancelled.[/yellow]")
        raise typer.Exit(0)
    except RuntimeError as exc:
        ticker.stop()
        console.print(f"\n  [red]Login failed:[/red] {exc}")
        raise typer.Exit(1)
    except Exception as exc:
        ticker.stop()
        console.print(f"\n  [red]Unexpected error:[/red] {exc}")
        raise typer.Exit(1)

    ticker.stop()

    # ── Save token ────────────────────────────────────────────────────────────
    TokenStore.save(result.token, result.username, result.scopes)

    # ── Screen 3: success ─────────────────────────────────────────────────────
    _print_banner()

    name_part = f" ({result.name})" if result.name and result.name != result.username else ""
    console.print(
        f"  [green]✓[/green]  Logged in as "
        f"[bold cyan]@{result.username}[/bold cyan][dim]{name_part}[/dim]"
    )
    console.print()
    console.print("  [dim]nexarq is ready.[/dim]  Run [cyan]nexarq run[/cyan] to review your last commit.")
    console.print()
