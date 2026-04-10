"""Config file management: load, save, merge, validate."""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import ValidationError

from nexarq_cli.config.schema import NexarqConfig

NEXARQ_HOME = Path(os.environ.get("NEXARQ_HOME", "~/.nexarq")).expanduser()
CONFIG_FILENAME = "config.yaml"


class ConfigManager:
    """Manages reading and writing ~/.nexarq/config.yaml (or profile variants)."""

    def __init__(self, home: Path = NEXARQ_HOME, profile: str = "default") -> None:
        self.home = home
        self.profile = profile
        self._config: NexarqConfig | None = None

    # ── paths ────────────────────────────────────────────────────────────────

    @property
    def config_dir(self) -> Path:
        if self.profile == "default":
            return self.home
        return self.home / "profiles" / self.profile

    @property
    def config_path(self) -> Path:
        return self.config_dir / CONFIG_FILENAME

    # ── load / save ──────────────────────────────────────────────────────────

    def load(self) -> NexarqConfig:
        """Load config from disk; return defaults if missing."""
        if self._config is not None:
            return self._config

        if not self.config_path.exists():
            self._config = NexarqConfig(profile=self.profile)
            return self._config

        raw = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        try:
            self._config = NexarqConfig(**raw)
        except ValidationError as exc:
            raise RuntimeError(
                f"Invalid config at {self.config_path}:\n{exc}"
            ) from exc

        return self._config

    def save(self, config: NexarqConfig | None = None) -> None:
        """Persist config to disk."""
        cfg = config or self._config or NexarqConfig()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        data = cfg.model_dump(mode="json", exclude_none=True)
        self.config_path.write_text(
            yaml.dump(data, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        self._config = cfg

    def ensure_dirs(self) -> None:
        """Create all required directories under NEXARQ_HOME."""
        for subdir in ("logs", "profiles", "mcp", "audit"):
            (self.home / subdir).mkdir(parents=True, exist_ok=True)

    # ── convenience ──────────────────────────────────────────────────────────

    def get(self) -> NexarqConfig:
        return self.load()

    def reset_cache(self) -> None:
        self._config = None

    @classmethod
    def for_project(cls, project_root: Path) -> "ConfigManager":
        """Check for a project-local .nexarq/config.yaml, fall back to home."""
        local = project_root / ".nexarq" / CONFIG_FILENAME
        if local.exists():
            mgr = cls(home=project_root / ".nexarq")
            return mgr
        return cls()

    def list_profiles(self) -> list[str]:
        profiles_dir = self.home / "profiles"
        if not profiles_dir.exists():
            return ["default"]
        names = ["default"] + [p.name for p in profiles_dir.iterdir() if p.is_dir()]
        return names
