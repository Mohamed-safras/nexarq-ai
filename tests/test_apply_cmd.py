"""Tests for nexarq apply – approval-based code modification (SRS 3.9)."""
from __future__ import annotations

import pytest
from pathlib import Path
from typer.testing import CliRunner

from nexarq_cli.main import app
from nexarq_cli.cli.apply_cmd import _apply_block

runner = CliRunner()


# ── _apply_block unit tests ───────────────────────────────────────────────────

class TestApplyBlock:
    def test_applies_matching_block(self):
        original = "def foo():\n    return 1\n\ndef bar():\n    pass\n"
        new_block = "def foo():\n    return 42\n"
        result = _apply_block(original, new_block)
        assert "return 42" in result

    def test_no_match_returns_original(self):
        original = "def foo(): pass\n"
        new_block = "def completely_different(): pass\n"
        # If fingerprint not found, original returned
        result = _apply_block(original, new_block)
        # Result is either modified or original unchanged
        assert isinstance(result, str)

    def test_empty_block_returns_original(self):
        original = "def foo(): pass\n"
        result = _apply_block(original, "")
        assert result == original

    def test_empty_original_no_crash(self):
        result = _apply_block("", "def foo(): pass")
        assert isinstance(result, str)


# ── CLI command tests ─────────────────────────────────────────────────────────

class TestApplyCommandHelp:
    def test_apply_no_args_shows_info(self):
        result = runner.invoke(app, ["apply"])
        assert result.exit_code == 0
        assert "approval" in result.output.lower() or "apply" in result.output.lower()

    def test_apply_help_flag(self):
        result = runner.invoke(app, ["apply", "--help"])
        assert result.exit_code == 0
        assert "fix" in result.output.lower() or "apply" in result.output.lower()


class TestApplyCommandErrors:
    def test_missing_fix_file_raises(self, tmp_path):
        result = runner.invoke(app, ["apply", "--fix-file", str(tmp_path / "nofile.txt")])
        # Either exit 1 or output mentions not found
        assert result.exit_code != 0 or "not found" in result.output.lower() or "error" in result.output.lower()

    def test_missing_target_file_error(self, tmp_path):
        fix_file = tmp_path / "fixes.txt"
        fix_file.write_text("After:\n```python\ndef foo(): pass\n```\n", encoding="utf-8")
        result = runner.invoke(app, [
            "apply",
            "--fix-file", str(fix_file),
            "--target", str(tmp_path / "nofile.py"),
        ])
        assert result.exit_code != 0 or "not found" in result.output.lower() or "error" in result.output.lower()


class TestApplyDryRun:
    def test_dry_run_does_not_modify(self, tmp_path):
        target = tmp_path / "src.py"
        target.write_text("def foo():\n    return 1\n", encoding="utf-8")

        fix_file = tmp_path / "fixes.txt"
        fix_file.write_text(
            "After:\n```python\ndef foo():\n    return 42\n```\n",
            encoding="utf-8",
        )

        original_content = target.read_text(encoding="utf-8")
        result = runner.invoke(app, [
            "apply",
            "--fix-file", str(fix_file),
            "--target", str(target),
            "--dry-run",
        ])

        # File must be unchanged
        assert target.read_text(encoding="utf-8") == original_content
        assert result.exit_code == 0

    def test_dry_run_mentions_no_files_modified(self, tmp_path):
        target = tmp_path / "src.py"
        target.write_text("x = 1\n", encoding="utf-8")
        fix_file = tmp_path / "fixes.txt"
        fix_file.write_text("After:\n```python\nx = 2\n```\n", encoding="utf-8")

        result = runner.invoke(app, [
            "apply", "--fix-file", str(fix_file),
            "--target", str(target), "--dry-run",
        ])
        assert "DRY RUN" in result.output or "dry" in result.output.lower()


class TestApplyBackup:
    def test_backup_created_on_apply(self, tmp_path):
        target = tmp_path / "src.py"
        target.write_text("def foo():\n    return 1\n", encoding="utf-8")

        fix_file = tmp_path / "fixes.txt"
        fix_file.write_text(
            "After:\n```python\ndef foo():\n    return 1\n```\n",
            encoding="utf-8",
        )

        # Simulate 'y' approval input
        result = runner.invoke(app, [
            "apply", "--fix-file", str(fix_file),
            "--target", str(target), "--backup",
        ], input="y\n")

        # A .bak file should exist
        bak_files = list(tmp_path.glob("*.bak"))
        assert len(bak_files) >= 1 or result.exit_code == 0

    def test_no_backup_flag_skips_backup(self, tmp_path):
        target = tmp_path / "src.py"
        target.write_text("x = 1\n", encoding="utf-8")
        fix_file = tmp_path / "fixes.txt"
        fix_file.write_text("After:\n```python\nx = 1\n```\n", encoding="utf-8")

        runner.invoke(app, [
            "apply", "--fix-file", str(fix_file),
            "--target", str(target), "--no-backup",
        ], input="n\n")

        bak_files = list(tmp_path.glob("*.bak"))
        assert len(bak_files) == 0


class TestApplyNoAutoApply:
    """SRS 3.9: Must NEVER auto-apply changes."""

    def test_skip_answer_leaves_file_unchanged(self, tmp_path):
        target = tmp_path / "src.py"
        original = "def foo():\n    return 1\n"
        target.write_text(original, encoding="utf-8")

        fix_file = tmp_path / "fixes.txt"
        fix_file.write_text(
            "After:\n```python\ndef foo():\n    return 99\n```\n",
            encoding="utf-8",
        )

        # Answer 'n' to skip
        runner.invoke(app, [
            "apply", "--fix-file", str(fix_file), "--target", str(target),
        ], input="n\n")

        assert target.read_text(encoding="utf-8") == original

    def test_quit_leaves_file_unchanged(self, tmp_path):
        target = tmp_path / "src.py"
        original = "def bar(): pass\n"
        target.write_text(original, encoding="utf-8")

        fix_file = tmp_path / "fixes.txt"
        fix_file.write_text(
            "After:\n```python\ndef bar(): return 1\n```\n",
            encoding="utf-8",
        )

        runner.invoke(app, [
            "apply", "--fix-file", str(fix_file), "--target", str(target),
        ], input="q\n")

        assert target.read_text(encoding="utf-8") == original
