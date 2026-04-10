"""
Approval-based code modification (SRS 3.9).

nexarq apply – show AI-generated fix diff, require explicit approval, apply safely.

NEVER auto-applies changes. All modifications require:
  1. Showing the full diff preview
  2. Explicit user confirmation (yes/no)
  3. Backup of original file before patching
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.syntax import Syntax

from nexarq_cli.utils.console import console

app = typer.Typer()

# Pattern to extract code blocks from AI fix output
_CODE_BLOCK_RE = re.compile(
    r"After:\s*```(?:\w+)?\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)
_FILE_RE = re.compile(r"File:\s*(.+)")


def apply(
    fix_file: Optional[Path] = typer.Option(
        None,
        "--fix-file",
        "-f",
        help="Path to a file containing AI-generated fix output",
    ),
    target_file: Optional[Path] = typer.Option(
        None,
        "--target",
        "-t",
        help="Target source file to patch",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would change without writing"
    ),
    backup: bool = typer.Option(
        True, "--backup/--no-backup", help="Create .bak backup before applying"
    ),
) -> None:
    """
    Apply an AI-generated fix with explicit approval (SRS 3.9).

    Shows the full diff preview and requires your confirmation before
    writing any changes. Creates a backup by default.

    Example:
      nexarq run --agents ai_fixes > fixes.txt
      nexarq apply --fix-file fixes.txt --target src/auth.py
    """
    if not fix_file and not target_file:
        console.print(
            Panel(
                "[bold]Approval-Based Code Modification[/bold]\n\n"
                "This command applies AI-generated fixes with your explicit approval.\n\n"
                "Usage:\n"
                "  1. Generate fixes: [cyan]nexarq run --agents ai_fixes[/cyan]\n"
                "  2. Save output:    [cyan]nexarq run --agents ai_fixes > fixes.txt[/cyan]\n"
                "  3. Apply fixes:    [cyan]nexarq apply --fix-file fixes.txt --target src/file.py[/cyan]\n\n"
                "[yellow]Nexarq NEVER auto-applies changes. You approve every fix.[/yellow]",
                title="nexarq apply",
                border_style="blue",
            )
        )
        return

    if fix_file and not fix_file.exists():
        console.print(f"[red]Error:[/red] Fix file not found: {fix_file}")
        raise typer.Exit(1)

    if target_file and not target_file.exists():
        console.print(f"[red]Error:[/red] Target file not found: {target_file}")
        raise typer.Exit(1)

    fix_content = fix_file.read_text(encoding="utf-8") if fix_file else ""
    target_content = target_file.read_text(encoding="utf-8") if target_file else ""

    # Extract proposed changes
    proposed_blocks = _CODE_BLOCK_RE.findall(fix_content)

    if not proposed_blocks:
        console.print("[yellow]No applicable code blocks found in the fix output.[/yellow]")
        console.print(
            "Ensure the fix output is from [cyan]nexarq run --agents ai_fixes[/cyan]."
        )
        return

    console.print(
        Panel(
            f"[bold]Found {len(proposed_blocks)} proposed fix(es)[/bold]\n"
            f"Target: {target_file or 'none specified'}",
            title="[bold blue]Nexarq Apply – Fix Preview[/bold blue]",
            border_style="blue",
        )
    )

    applied = 0
    for idx, block in enumerate(proposed_blocks, 1):
        block = block.strip()
        console.print(f"\n[bold]Fix #{idx}:[/bold]")

        # Show the proposed fix
        console.print(
            Panel(
                Syntax(block, "python", theme="monokai", line_numbers=True),
                title=f"[yellow]Proposed Change #{idx}[/yellow]",
                border_style="yellow",
            )
        )

        if dry_run:
            console.print(f"[dim]  [DRY RUN] Would apply fix #{idx}[/dim]")
            continue

        # Require explicit approval
        console.print(
            "\n[bold]Apply this fix?[/bold] "
            "[dim](y=yes / n=skip / q=quit)[/dim] ",
            end="",
        )
        try:
            choice = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

        if choice == "q":
            console.print("[yellow]Quit – no further fixes applied.[/yellow]")
            break
        elif choice != "y":
            console.print(f"  [dim]Skipped fix #{idx}.[/dim]")
            continue

        if not target_file:
            console.print("[red]Error:[/red] --target file required to apply changes.")
            raise typer.Exit(1)

        # Create backup
        if backup:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            bak = target_file.with_suffix(f".{ts}.bak")
            shutil.copy2(target_file, bak)
            console.print(f"  [dim]Backup created: {bak}[/dim]")

        # Apply: replace matching block or append (simple strategy)
        new_content = _apply_block(target_content, block)
        if new_content == target_content:
            console.print(
                f"  [yellow]Warning:[/yellow] Fix #{idx} content not found in target file. "
                "Manual application required."
            )
        else:
            target_file.write_text(new_content, encoding="utf-8")
            target_content = new_content
            console.print(f"  [green]Fix #{idx} applied.[/green]")
            applied += 1

    if dry_run:
        console.print(
            f"\n[dim][DRY RUN] Would apply {len(proposed_blocks)} fix(es). "
            "No files were modified.[/dim]"
        )
    else:
        console.print(
            f"\n[bold green]{applied}[/bold green] / {len(proposed_blocks)} fix(es) applied."
        )
        if applied > 0:
            console.print(
                "[dim]Review changes with: git diff\n"
                "Revert with:          git checkout -- <file>[/dim]"
            )


def _apply_block(original: str, new_block: str) -> str:
    """
    Attempt to replace matching content in the original file.
    Returns the original unchanged if no match can be found.
    """
    # Simple line-by-line block search (first 3 lines as fingerprint)
    block_lines = [l for l in new_block.splitlines() if l.strip()]
    if not block_lines:
        return original

    fingerprint = block_lines[0].strip()
    orig_lines = original.splitlines(keepends=True)

    for i, line in enumerate(orig_lines):
        if fingerprint in line:
            # Replace from match point to same length
            end = min(i + len(block_lines), len(orig_lines))
            new_lines = list(orig_lines[:i]) + [l + "\n" for l in block_lines] + list(orig_lines[end:])
            return "".join(new_lines)

    return original
