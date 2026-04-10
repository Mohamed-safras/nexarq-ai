"""
Scenarios: CLI command integration tests using Typer's test runner.
Tests all commands without needing Ollama or real git repos.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from nexarq_cli.main import app

runner = CliRunner()


# ── --help / --version ────────────────────────────────────────────────────────

class TestCLIHelp:
    def test_root_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "init" in result.output
        assert "doctor" in result.output
        assert "run" in result.output
        assert "config" in result.output
        assert "hook" in result.output
        assert "mcp" in result.output

    def test_version(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "nexarq-cli" in result.output

    def test_config_help(self):
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "show" in result.output
        assert "set-key" in result.output

    def test_hook_help(self):
        result = runner.invoke(app, ["hook", "--help"])
        assert result.exit_code == 0
        assert "install" in result.output
        assert "uninstall" in result.output

    def test_mcp_help(self):
        result = runner.invoke(app, ["mcp", "--help"])
        assert result.exit_code == 0
        assert "add" in result.output
        assert "remove" in result.output


# ── nexarq init ───────────────────────────────────────────────────────────────

class TestInitCommand:
    def test_init_non_interactive(self, tmp_path):
        with patch("nexarq_cli.cli.init_cmd.ConfigManager") as MockMgr:
            mock_mgr = MagicMock()
            mock_mgr.config_path = tmp_path / "config.yaml"
            MockMgr.return_value = mock_mgr

            result = runner.invoke(app, ["init", "--yes"])
            assert result.exit_code == 0
            assert "Initialized" in result.output or "Config saved" in result.output


# ── nexarq doctor ─────────────────────────────────────────────────────────────

class TestDoctorCommand:
    def test_doctor_runs(self):
        result = runner.invoke(app, ["doctor"])
        # exit 0 or 1 is fine — just must not crash
        assert result.exit_code in (0, 1)
        assert "Python version" in result.output

    def test_doctor_shows_dependencies(self):
        result = runner.invoke(app, ["doctor"])
        assert "typer" in result.output
        assert "rich" in result.output

    def test_doctor_shows_api_key_status(self):
        result = runner.invoke(app, ["doctor"])
        assert "openai" in result.output
        assert "anthropic" in result.output


# ── nexarq run ────────────────────────────────────────────────────────────────

class TestRunCommand:
    def test_list_agents(self):
        result = runner.invoke(app, ["run", "--list-agents"])
        assert result.exit_code == 0
        assert "security" in result.output
        assert "bugs" in result.output
        assert "22" in result.output or len([l for l in result.output.splitlines() if "medium" in l.lower() or "high" in l.lower() or "critical" in l.lower()]) > 0

    def test_run_with_diff_file(self, tmp_path):
        diff = tmp_path / "test.patch"
        diff.write_text("""\
diff --git a/app.py b/app.py
@@ -1,3 +1,5 @@
+import os
+secret = os.environ.get('KEY', 'fallback')
 def main():
-    pass
+    print(secret)
""")
        from nexarq_cli.llm.base import LLMResponse
        mock_response = LLMResponse(
            text="No issues found.", provider="mock", model="mock",
            prompt_tokens=10, completion_tokens=20,
        )
        with patch("nexarq_cli.llm.factory.LLMFactory.get_for_agent") as mock_factory:
            mock_provider = MagicMock()
            mock_provider.complete.return_value = mock_response
            mock_factory.return_value = mock_provider

            result = runner.invoke(app, [
                "run",
                "--diff", str(diff),
                "--agents", "review",
                "--no-interactive",
            ])

        assert result.exit_code == 0

    def test_run_no_diff_file_not_found(self, tmp_path):
        result = runner.invoke(app, ["run", "--diff", str(tmp_path / "nonexistent.patch")])
        assert result.exit_code != 0 or "Could not" in result.output or "not found" in result.output.lower()


# ── nexarq config ─────────────────────────────────────────────────────────────

class TestConfigCommand:
    def test_config_show(self, tmp_path):
        with patch("nexarq_cli.cli.config_cmd.ConfigManager") as MockMgr:
            mock_mgr = MagicMock()
            mock_mgr.config_path = tmp_path / "config.yaml"
            from nexarq_cli.config.schema import NexarqConfig
            mock_mgr.load.return_value = NexarqConfig()
            MockMgr.return_value = mock_mgr

            result = runner.invoke(app, ["config", "show"])
            assert result.exit_code == 0

    def test_config_set_agents(self, tmp_path):
        with patch("nexarq_cli.cli.config_cmd.ConfigManager") as MockMgr:
            mock_mgr = MagicMock()
            from nexarq_cli.config.schema import NexarqConfig
            mock_mgr.load.return_value = NexarqConfig()
            MockMgr.return_value = mock_mgr

            result = runner.invoke(app, ["config", "set-agents", "security,bugs"])
            assert result.exit_code == 0

    def test_config_cloud_consent_true(self, tmp_path):
        with patch("nexarq_cli.cli.config_cmd.ConfigManager") as MockMgr:
            mock_mgr = MagicMock()
            from nexarq_cli.config.schema import NexarqConfig
            mock_mgr.load.return_value = NexarqConfig()
            MockMgr.return_value = mock_mgr

            result = runner.invoke(app, ["config", "cloud-consent", "true"])
            assert result.exit_code == 0

    def test_config_list_profiles(self):
        with patch("nexarq_cli.cli.config_cmd.ConfigManager") as MockMgr:
            mock_mgr = MagicMock()
            mock_mgr.list_profiles.return_value = ["default", "work"]
            MockMgr.return_value = mock_mgr

            result = runner.invoke(app, ["config", "list-profiles"])
            assert result.exit_code == 0


# ── nexarq hook ───────────────────────────────────────────────────────────────

class TestHookCommand:
    def test_hook_status(self):
        with patch("nexarq_cli.cli.hook_cmd.HookInstaller") as MockInstaller:
            mock_installer = MagicMock()
            mock_installer.status.return_value = {
                "post-commit": "nexarq",
                "pre-push": "not installed",
            }
            MockInstaller.return_value = mock_installer

            result = runner.invoke(app, ["hook", "status"])
            assert result.exit_code == 0

    def test_hook_install_post_commit(self, tmp_path):
        with patch("nexarq_cli.cli.hook_cmd.HookInstaller") as MockInstaller:
            mock_installer = MagicMock()
            mock_installer.install.return_value = tmp_path / "post-commit"
            MockInstaller.return_value = mock_installer

            result = runner.invoke(app, ["hook", "install", "post-commit"])
            assert result.exit_code == 0

    def test_hook_uninstall(self):
        with patch("nexarq_cli.cli.hook_cmd.HookInstaller") as MockInstaller:
            mock_installer = MagicMock()
            mock_installer.uninstall.return_value = True
            MockInstaller.return_value = mock_installer

            result = runner.invoke(app, ["hook", "uninstall", "post-commit"])
            assert result.exit_code == 0

    def test_hook_invalid_type(self):
        result = runner.invoke(app, ["hook", "install", "invalid-hook"])
        assert result.exit_code != 0


# ── nexarq mcp ────────────────────────────────────────────────────────────────

class TestMCPCommand:
    def test_mcp_list_empty(self):
        with patch("nexarq_cli.cli.mcp_cmd.ConfigManager") as MockMgr:
            mock_mgr = MagicMock()
            from nexarq_cli.config.schema import NexarqConfig
            mock_mgr.load.return_value = NexarqConfig()
            MockMgr.return_value = mock_mgr

            result = runner.invoke(app, ["mcp", "list"])
            assert result.exit_code == 0
            assert "No MCP servers" in result.output

    def test_mcp_add_local_server(self):
        with patch("nexarq_cli.cli.mcp_cmd.ConfigManager") as MockMgr:
            mock_mgr = MagicMock()
            from nexarq_cli.config.schema import NexarqConfig
            cfg = NexarqConfig()
            mock_mgr.load.return_value = cfg
            MockMgr.return_value = mock_mgr

            result = runner.invoke(app, [
                "mcp", "add", "my-scanner",
                "http://localhost:8090",
                "--local",
                "--tools", "scan,lint",
            ])
            assert result.exit_code == 0

    def test_mcp_add_remote_without_consent_fails(self):
        result = runner.invoke(app, [
            "mcp", "add", "remote",
            "http://remote.example.com",
            "--remote",
        ])
        assert result.exit_code != 0
        assert "consent" in result.output.lower()


# ── nexarq help ───────────────────────────────────────────────────────────────

class TestHelpCommand:
    def test_help_shows_content(self):
        result = runner.invoke(app, ["help"])
        assert result.exit_code == 0
        assert "nexarq" in result.output.lower()

    def test_help_agents_topic(self):
        result = runner.invoke(app, ["help", "agents"])
        assert result.exit_code == 0
        assert "security" in result.output

    def test_help_security_topic(self):
        result = runner.invoke(app, ["help", "security"])
        assert result.exit_code == 0
        assert "SEC-" in result.output or "redact" in result.output.lower()

    def test_help_config_topic(self):
        result = runner.invoke(app, ["help", "config"])
        assert result.exit_code == 0
        assert "config.yaml" in result.output
