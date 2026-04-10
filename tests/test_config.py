"""Tests for config schema and manager."""
import tempfile
from pathlib import Path

import pytest

from nexarq_cli.config.schema import (
    NexarqConfig, ProviderConfig, ProviderName, AgentConfig, AgentPermissions
)
from nexarq_cli.config.manager import ConfigManager


class TestNexarqConfig:
    def test_defaults(self):
        cfg = NexarqConfig()
        assert cfg.default_agents == []  # empty = auto-select from diff context
        assert "default" in cfg.providers
        assert cfg.providers["default"].name == "ollama"
        assert cfg.privacy.cloud_consent is False

    def test_effective_provider_fallback(self):
        cfg = NexarqConfig()
        # Unknown agent falls back to default provider
        provider = cfg.effective_provider("nonexistent_agent")
        assert provider.name == "ollama"

    def test_effective_agent_config_default(self):
        cfg = NexarqConfig()
        agent_cfg = cfg.effective_agent_config("security")
        assert agent_cfg.enabled is True

    def test_provider_temperature_clamp(self):
        p = ProviderConfig(temperature=0.12345)
        assert p.temperature == 0.12

    def test_agent_permissions_defaults(self):
        p = AgentPermissions()
        assert p.read_diff_only is True
        assert p.execute_code is False  # SEC-7/8 – never executable
        assert p.network_access is False


class TestConfigManager:
    def test_load_creates_defaults_when_missing(self, tmp_path):
        mgr = ConfigManager(home=tmp_path)
        cfg = mgr.load()
        assert isinstance(cfg, NexarqConfig)

    def test_save_and_reload(self, tmp_path):
        mgr = ConfigManager(home=tmp_path)
        cfg = mgr.load()
        cfg.default_agents = ["security", "bugs"]
        mgr.save(cfg)

        mgr2 = ConfigManager(home=tmp_path)
        loaded = mgr2.load()
        assert loaded.default_agents == ["security", "bugs"]

    def test_ensure_dirs_creates_structure(self, tmp_path):
        mgr = ConfigManager(home=tmp_path)
        mgr.ensure_dirs()
        assert (tmp_path / "logs").is_dir()
        assert (tmp_path / "profiles").is_dir()

    def test_list_profiles_default(self, tmp_path):
        mgr = ConfigManager(home=tmp_path)
        profiles = mgr.list_profiles()
        assert "default" in profiles
