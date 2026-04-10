"""Tests for nexarq enable / disable commands (SRS 3.10)."""
from __future__ import annotations

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from nexarq_cli.main import app
from nexarq_cli.config.schema import NexarqConfig

runner = CliRunner()


class TestEnableCommand:
    def test_enable_exits_zero(self):
        cfg = NexarqConfig()
        with patch("nexarq_cli.cli.enable_cmd.ConfigManager") as MockMgr:
            mock_mgr = MagicMock()
            mock_mgr.load.return_value = cfg
            MockMgr.return_value = mock_mgr

            result = runner.invoke(app, ["enable"])
            assert result.exit_code == 0

    def test_enable_sets_flag_and_saves(self):
        cfg = NexarqConfig(enabled=False)
        with patch("nexarq_cli.cli.enable_cmd.ConfigManager") as MockMgr:
            mock_mgr = MagicMock()
            mock_mgr.load.return_value = cfg
            MockMgr.return_value = mock_mgr

            runner.invoke(app, ["enable"])
            assert cfg.enabled is True
            mock_mgr.save.assert_called_once_with(cfg)

    def test_enable_output_contains_enabled(self):
        cfg = NexarqConfig()
        with patch("nexarq_cli.cli.enable_cmd.ConfigManager") as MockMgr:
            mock_mgr = MagicMock()
            mock_mgr.load.return_value = cfg
            MockMgr.return_value = mock_mgr

            result = runner.invoke(app, ["enable"])
            assert "enabled" in result.output.lower()

    def test_enable_with_profile(self):
        cfg = NexarqConfig()
        with patch("nexarq_cli.cli.enable_cmd.ConfigManager") as MockMgr:
            mock_mgr = MagicMock()
            mock_mgr.load.return_value = cfg
            MockMgr.return_value = mock_mgr

            result = runner.invoke(app, ["enable", "--profile", "myteam"])
            assert result.exit_code == 0
            MockMgr.assert_called_with(profile="myteam")


class TestDisableCommand:
    def test_disable_exits_zero(self):
        cfg = NexarqConfig()
        with patch("nexarq_cli.cli.disable_cmd.ConfigManager") as MockMgr:
            mock_mgr = MagicMock()
            mock_mgr.load.return_value = cfg
            MockMgr.return_value = mock_mgr

            result = runner.invoke(app, ["disable"])
            assert result.exit_code == 0

    def test_disable_clears_flag(self):
        cfg = NexarqConfig(enabled=True)
        with patch("nexarq_cli.cli.disable_cmd.ConfigManager") as MockMgr:
            mock_mgr = MagicMock()
            mock_mgr.load.return_value = cfg
            MockMgr.return_value = mock_mgr

            runner.invoke(app, ["disable"])
            assert cfg.enabled is False
            mock_mgr.save.assert_called_once_with(cfg)

    def test_disable_output_contains_disabled(self):
        cfg = NexarqConfig()
        with patch("nexarq_cli.cli.disable_cmd.ConfigManager") as MockMgr:
            mock_mgr = MagicMock()
            mock_mgr.load.return_value = cfg
            MockMgr.return_value = mock_mgr

            result = runner.invoke(app, ["disable"])
            assert "disabled" in result.output.lower()

    def test_disable_mentions_reenable(self):
        cfg = NexarqConfig()
        with patch("nexarq_cli.cli.disable_cmd.ConfigManager") as MockMgr:
            mock_mgr = MagicMock()
            mock_mgr.load.return_value = cfg
            MockMgr.return_value = mock_mgr

            result = runner.invoke(app, ["disable"])
            assert "enable" in result.output.lower()


class TestRunRespectsEnabledFlag:
    """Verify nexarq run respects the enabled flag."""

    def test_run_exits_when_disabled(self):
        cfg = NexarqConfig(enabled=False)
        with patch("nexarq_cli.cli.run_cmd.ConfigManager") as MockMgr:
            mock_mgr = MagicMock()
            mock_mgr.load.return_value = cfg
            mock_mgr.home = MagicMock()
            mock_mgr.home.__truediv__ = lambda s, p: MagicMock(exists=lambda: False)
            MockMgr.return_value = mock_mgr

            result = runner.invoke(app, ["run"])
            assert result.exit_code == 0
            assert "disabled" in result.output.lower()

    def test_run_proceeds_when_enabled(self):
        cfg = NexarqConfig(enabled=True)
        with patch("nexarq_cli.cli.run_cmd.ConfigManager") as MockMgr, \
             patch("nexarq_cli.cli.run_cmd.DiffEngine") as MockEngine, \
             patch("nexarq_cli.cli.run_cmd.LLMFactory"), \
             patch("nexarq_cli.cli.run_cmd.SecretsManager"), \
             patch("nexarq_cli.cli.run_cmd.AuditLogger"), \
             patch("nexarq_cli.cli.run_cmd.AgentOrchestrator"):

            mock_mgr = MagicMock()
            mock_mgr.load.return_value = cfg
            standards = MagicMock()
            standards.exists.return_value = False
            mock_mgr.home.__truediv__ = lambda s, p: standards
            MockMgr.return_value = mock_mgr

            mock_diff = MagicMock()
            mock_diff.files = []
            MockEngine.return_value.last_commit.return_value = mock_diff

            result = runner.invoke(app, ["run"])
            # Should proceed past the enabled check (may exit for other reasons)
            assert "disabled" not in result.output.lower()
