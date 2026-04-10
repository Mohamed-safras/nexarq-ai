"""
LangChain LLM bridge.

Converts a Nexarq provider config into the appropriate LangChain
BaseChatModel so that LangGraph / LangChain tools work seamlessly with
whatever LLM the user has configured (Ollama, OpenAI, Anthropic, …).

Usage:
    from nexarq_cli.frameworks.lc_llm import get_lc_llm
    llm = get_lc_llm(cfg, profile="default")
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from nexarq_cli.config.schema import NexarqConfig


def get_lc_llm(cfg: "NexarqConfig", profile: str = "default") -> "BaseChatModel":
    """
    Return a LangChain BaseChatModel backed by the configured provider.

    Supports:
      - ollama   → ChatOllama       (langchain-ollama)
      - openai   → ChatOpenAI       (langchain-openai)
      - anthropic → ChatAnthropic   (langchain-anthropic)
      - google   → ChatGoogleGenerativeAI (langchain-google-genai)

    Raises ImportError if the required langchain provider package is missing.
    Raises ValueError if the provider is not recognised.
    """
    provider_cfg = cfg.providers.get(profile) or next(iter(cfg.providers.values()))
    name = str(provider_cfg.name.value if hasattr(provider_cfg.name, "value") else provider_cfg.name)
    model = provider_cfg.model
    temperature = getattr(provider_cfg, "temperature", 0.2)

    if name == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise ImportError(
                "langchain-ollama not installed.\n"
                "Run: pip install 'nexarq-cli[langchain]'  or  pip install langchain-ollama"
            )
        return ChatOllama(
            model=model,
            temperature=temperature,
        )

    if name == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("langchain-openai not installed. Run: pip install langchain-openai")
        import os
        api_key = getattr(provider_cfg, "api_key", None) or os.environ.get("OPENAI_API_KEY", "")
        return ChatOpenAI(model=model, temperature=temperature, api_key=api_key)

    if name == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError("langchain-anthropic not installed. Run: pip install langchain-anthropic")
        import os
        api_key = getattr(provider_cfg, "api_key", None) or os.environ.get("ANTHROPIC_API_KEY", "")
        return ChatAnthropic(model=model, temperature=temperature, api_key=api_key)

    if name == "google":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError("langchain-google-genai not installed. Run: pip install langchain-google-genai")
        return ChatGoogleGenerativeAI(model=model, temperature=temperature)

    raise ValueError(
        f"Provider '{name}' is not supported by the LangChain bridge. "
        "Supported: ollama, openai, anthropic, google"
    )
