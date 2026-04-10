"""LLM provider factory – resolves config to a concrete provider (PR-1/2/3)."""
from __future__ import annotations

from nexarq_cli.config.schema import NexarqConfig, ProviderConfig, ProviderName
from nexarq_cli.llm.base import BaseLLMProvider
from nexarq_cli.security.secrets import SecretsManager


class LLMFactory:
    """
    Build provider instances from configuration.
    Handles API key retrieval, fallback chaining, and runtime switching.
    """

    def __init__(self, config: NexarqConfig, secrets: SecretsManager) -> None:
        self._config = config
        self._secrets = secrets
        self._cache: dict[str, BaseLLMProvider] = {}

    def get(self, provider_key: str = "default") -> BaseLLMProvider:
        """Resolve a provider key to a ready-to-use provider instance."""
        if provider_key in self._cache:
            return self._cache[provider_key]

        provider_cfg = self._config.providers.get(
            provider_key,
            self._config.providers.get("default", ProviderConfig()),
        )

        try:
            instance = self._build(provider_cfg)
        except Exception as exc:
            # Fallback chain (PR-2)
            if provider_cfg.fallback:
                fallback_cfg = self._config.providers.get(
                    provider_cfg.fallback.value,
                    ProviderConfig(name=provider_cfg.fallback),
                )
                instance = self._build(fallback_cfg)
            else:
                raise RuntimeError(
                    f"Cannot build LLM provider '{provider_key}': {exc}"
                ) from exc

        self._cache[provider_key] = instance
        return instance

    def get_for_agent(self, agent_name: str) -> BaseLLMProvider:
        """Convenience: resolve the provider assigned to a specific agent."""
        agent_cfg = self._config.effective_agent_config(agent_name)
        return self.get(agent_cfg.provider)

    def invalidate(self, provider_key: str | None = None) -> None:
        """Flush cached instances for runtime switching (PR-3)."""
        if provider_key:
            self._cache.pop(provider_key, None)
        else:
            self._cache.clear()

    # ── internal ─────────────────────────────────────────────────────────────

    def _build(self, cfg: ProviderConfig) -> BaseLLMProvider:
        name = ProviderName(cfg.name)

        if name == ProviderName.OLLAMA:
            from nexarq_cli.llm.ollama import OllamaProvider
            base_url = cfg.base_url or "http://localhost:11434"
            # Auto-discover model if not specified
            model = cfg.model or _discover_ollama_model(base_url)
            return OllamaProvider(
                model=model,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                timeout=cfg.timeout,
                base_url=base_url,
            )

        # Cloud providers require API keys (PR-4 / SEC-1)
        api_key = self._secrets.get_key(name.value)
        if not api_key:
            raise RuntimeError(
                f"No API key found for provider '{name.value}'. "
                f"Run: nexarq config set-key {name.value}"
            )

        if name == ProviderName.OPENAI:
            from nexarq_cli.llm.openai_provider import OpenAIProvider
            model = cfg.model or _discover_openai_model(api_key)
            return OpenAIProvider(
                api_key=api_key,
                model=model,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                timeout=cfg.timeout,
            )

        if name == ProviderName.ANTHROPIC:
            from nexarq_cli.llm.anthropic_provider import AnthropicProvider
            model = cfg.model or _discover_anthropic_model(api_key)
            return AnthropicProvider(
                api_key=api_key,
                model=model,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                timeout=cfg.timeout,
            )

        if name == ProviderName.GOOGLE:
            from nexarq_cli.llm.google_provider import GoogleProvider
            model = cfg.model or _discover_google_model(api_key)
            return GoogleProvider(
                api_key=api_key,
                model=model,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                timeout=cfg.timeout,
            )

        raise ValueError(f"Unknown provider: {cfg.name}")


# ── Runtime model discovery ───────────────────────────────────────────────────

def _discover_ollama_model(base_url: str) -> str:
    """
    Query Ollama at runtime for available models.
    Returns the first available code-capable model, or a sensible fallback.
    Exact tag matches (e.g. kimi-k2.5:cloud) take priority over partial matches.
    """
    # Preference order for code review tasks — exact full names tried first,
    # then base-name prefix matching as a fallback.
    preferred_exact = [
        "kimi-k2.5:cloud",
        "qwen2.5-coder:0.5b",
        "codellama:latest",
    ]
    preferred_prefix = [
        "kimi-k2.5", "deepseek-coder", "codellama", "qwen2.5-coder",
        "starcoder2", "codegemma", "granite-code", "llama3", "llama2",
        "mistral", "mixtral", "phi3", "gemma2",
    ]
    try:
        import httpx
        resp = httpx.get(f"{base_url}/api/tags", timeout=5)
        if resp.status_code == 200:
            available = [m["name"] for m in resp.json().get("models", [])]
            # 1. Exact full-name match (highest priority)
            for exact in preferred_exact:
                if exact in available:
                    return exact
            # 2. Prefix/substring match
            for pref in preferred_prefix:
                for name in available:
                    if pref in name.lower():
                        return name
            # 3. First available model
            if available:
                return available[0]
    except Exception:
        pass
    return "codellama:latest"   # Last-resort default if Ollama unreachable


def _discover_openai_model(api_key: str) -> str:
    """
    Pick the best available OpenAI model for code review.
    Queries the models list and prefers GPT-4 variants.
    """
    preferred = ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, timeout=10)
        available = {m.id for m in client.models.list().data}
        for p in preferred:
            if p in available:
                return p
    except Exception:
        pass
    return "gpt-4o"


def _discover_anthropic_model(api_key: str) -> str:
    """Pick the best available Anthropic model for code review."""
    preferred = [
        "claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001",
        "claude-opus-4", "claude-sonnet-4", "claude-3-5-sonnet-20241022",
    ]
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key, timeout=10)
        available = {m.id for m in client.models.list().data}
        for p in preferred:
            if p in available:
                return p
    except Exception:
        pass
    return "claude-sonnet-4-6"


def _discover_google_model(api_key: str) -> str:
    """Pick the best available Google model for code review."""
    preferred = ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"]
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        available = {m.name.split("/")[-1] for m in client.models.list()}
        for p in preferred:
            if p in available:
                return p
    except Exception:
        pass
    return "gemini-1.5-pro"
