"""Pydantic schemas for all Nexarq CLI configuration."""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ProviderName(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""

    name: ProviderName = ProviderName.OLLAMA
    model: str = ""                      # Empty = auto-discover at runtime
    base_url: str | None = None          # For Ollama overrides
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=128, le=128_000)
    timeout: int = Field(default=120, ge=10, le=600)
    fallback: ProviderName | None = None

    @field_validator("temperature")
    @classmethod
    def clamp_temperature(cls, v: float) -> float:
        return round(v, 2)


class AgentPermissions(BaseModel):
    """Explicit permission set every agent must declare."""

    read_diff_only: bool = True          # Default: diff-only access
    read_full_repo: bool = False
    network_access: bool = False
    execute_code: bool = False           # Always False – SEC-7/8
    mcp_access: bool = False


class AgentConfig(BaseModel):
    """Per-agent configuration."""

    enabled: bool = True
    provider: str = "default"           # Key into providers map
    permissions: AgentPermissions = Field(default_factory=AgentPermissions)
    token_limit: int = Field(default=4096, ge=128, le=128_000)
    temperature: float | None = None    # Override provider temperature
    output_format: Literal["text", "json", "markdown"] = "markdown"
    severity_threshold: Literal["critical", "high", "medium", "low", "all"] = "all"


class MCPServerConfig(BaseModel):
    """Single MCP server registration."""

    name: str
    uri: str
    local: bool = True
    enabled: bool = True
    allowed_tools: list[str] = Field(default_factory=list)  # Empty = none allowed
    timeout: int = 30
    consent_given: bool = False         # Remote servers require explicit consent


class GitConfig(BaseModel):
    """Git integration settings."""

    post_commit: bool = True
    pre_push: bool = False
    diff_only: bool = True
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["*.lock", "*.min.js", "dist/*", "build/*", "*.pb.go"]
    )
    max_diff_lines: int = Field(default=5000, ge=100, le=50_000)


class PrivacyConfig(BaseModel):
    """Data privacy controls (PR-5/6/7)."""

    cloud_consent: bool = False         # Must be explicitly enabled
    redact_patterns: list[str] = Field(
        default_factory=lambda: [
            r"(?i)(api[_-]?key|secret|password|token|credential)\s*=\s*\S+",
            r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*",
            r"-----BEGIN\s+\w+\s+PRIVATE KEY-----",
        ]
    )
    send_file_paths: bool = False       # Never send absolute paths


class AuditConfig(BaseModel):
    """Audit and logging settings (SEC-16/17/18)."""

    enabled: bool = True
    log_level: LogLevel = LogLevel.INFO
    log_dir: Path = Path("~/.nexarq/logs").expanduser()
    max_log_size_mb: int = 50
    retention_days: int = 30
    log_api_calls: bool = True
    log_agent_actions: bool = True


class TokenBudgetConfig(BaseModel):
    """Token governance settings (SRS 3.11)."""

    enabled: bool = False
    max_tokens_per_run: int = Field(default=0, ge=0)   # 0 = unlimited
    warn_at_percent: int = Field(default=80, ge=10, le=99)
    track_cost: bool = True
    # Cost rates per 1K tokens in USD — kept up to date by user
    cost_rates: dict[str, dict[str, float]] = Field(default_factory=lambda: {
        "openai":    {"prompt": 0.003,  "completion": 0.006},
        "anthropic": {"prompt": 0.003,  "completion": 0.015},
        "google":    {"prompt": 0.002,  "completion": 0.006},
        "ollama":    {"prompt": 0.0,    "completion": 0.0},
    })


class ExecutionTierConfig(BaseModel):
    """
    Tiered agent execution — controls cost vs. depth trade-off.

    Tier 1 (fast):  Always runs. Cheap, regex-assisted agents.
                    Catches secrets, obvious bugs, critical security.
    Tier 2 (smart): Diff-context selected. Runs agents relevant to what changed.
                    Skips irrelevant agents (e.g. i18n on a Python backend diff).
    Tier 3 (deep):  Tool-augmented ReAct agents. Runs only when Tier 1/2
                    found CRITICAL or HIGH issues. Most expensive.

    Set mode = "fast" to only run Tier 1 (CI gates, pre-push hooks).
    Set mode = "smart" (default) for Tier 1 + Tier 2.
    Set mode = "deep" to run all tiers including tool-augmented agents.
    Set mode = "auto" to escalate: start smart, promote to deep if CRITICAL found.
    """
    mode: Literal["fast", "smart", "deep", "auto"] = "smart"

    # Mode used when triggered by a git hook (post-commit, pre-push).
    # Defaults to "fast" so commits don't feel slow — only 3 agents run.
    # Set to "smart" or "deep" if you want full review on every commit.
    hook_mode: Literal["fast", "smart", "deep", "auto"] = "fast"

    # Max agents to run per run (0 = no limit)
    max_agents: int = Field(default=0, ge=0)

    # Max tool calls per agentic agent (prevents runaway ReAct loops)
    max_tool_calls_per_agent: int = Field(default=5, ge=1, le=20)

    # Minimum severity to trigger Tier 3 in "auto" mode
    deep_trigger_severity: Literal["critical", "high"] = "critical"

    # Agents always in Tier 1 (fast, always run regardless of mode)
    tier1_agents: list[str] = Field(default_factory=lambda: [
        "secrets_detection", "security", "bugs",
    ])


class NexarqConfig(BaseModel):
    """Root configuration schema for Nexarq CLI."""

    version: str = "1"
    profile: str = "default"
    enabled: bool = True                                # SRS 3.10 enable/disable

    # Provider map: key → ProviderConfig
    providers: dict[str, ProviderConfig] = Field(
        default_factory=lambda: {"default": ProviderConfig()}
    )

    # Agent map: agent_name → AgentConfig
    agents: dict[str, AgentConfig] = Field(default_factory=dict)

    # Which agents to run by default.
    # Empty list = fully auto-select from diff context at runtime (recommended).
    default_agents: list[str] = Field(default_factory=list)

    mcp_servers: list[MCPServerConfig] = Field(default_factory=list)
    git: GitConfig = Field(default_factory=GitConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    token_budget: TokenBudgetConfig = Field(default_factory=TokenBudgetConfig)
    execution: ExecutionTierConfig = Field(default_factory=ExecutionTierConfig)

    # GitHub OAuth App client ID for `nexarq login`.
    # Device-flow client_id is public (not a secret).
    # Override via env var:  NEXARQ_GITHUB_CLIENT_ID=Ov23li...
    github_client_id: str = Field(
        default="",
        description="GitHub OAuth App client ID for nexarq login",
    )

    def effective_agent_config(self, agent_name: str) -> AgentConfig:
        """Return merged agent config (explicit overrides defaults)."""
        return self.agents.get(agent_name, AgentConfig())

    def effective_provider(self, agent_name: str) -> ProviderConfig:
        """Resolve which provider an agent should use."""
        agent_cfg = self.effective_agent_config(agent_name)
        key = agent_cfg.provider
        return self.providers.get(key, self.providers.get("default", ProviderConfig()))

    model_config = {"use_enum_values": True}
