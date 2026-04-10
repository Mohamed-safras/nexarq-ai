"""
Scenarios: LLM provider factory, fallback chain, cloud consent,
           API key resolution, runtime switching.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nexarq_cli.config.schema import NexarqConfig, ProviderConfig, ProviderName
from nexarq_cli.llm.base import BaseLLMProvider, LLMResponse
from nexarq_cli.llm.factory import LLMFactory
from nexarq_cli.security.secrets import SecretsManager


# ── Helpers ───────────────────────────────────────────────────────────────────

class _FakeProvider(BaseLLMProvider):
    name = "fake"
    def _call_api(self, prompt, system=""):
        return LLMResponse(text="fake response", provider="fake", model=self.model)
    def health_check(self):
        return True


class _FailProvider(BaseLLMProvider):
    name = "fail"
    def _call_api(self, prompt, system=""):
        raise RuntimeError("Provider down")
    def health_check(self):
        return False


# ── LLMResponse ───────────────────────────────────────────────────────────────

class TestLLMResponse:
    def test_total_tokens(self):
        r = LLMResponse(text="hi", provider="ollama", model="x",
                        prompt_tokens=10, completion_tokens=20)
        assert r.total_tokens == 30

    def test_repr(self):
        p = _FakeProvider(model="test-model")
        assert "test-model" in repr(p)


# ── OllamaProvider ────────────────────────────────────────────────────────────

class TestOllamaProvider:
    def test_health_check_unreachable(self):
        from nexarq_cli.llm.ollama import OllamaProvider
        p = OllamaProvider(base_url="http://localhost:19999")
        assert p.health_check() is False

    def test_health_check_reachable(self):
        from nexarq_cli.llm.ollama import OllamaProvider
        import httpx
        with patch.object(httpx, "get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            p = OllamaProvider()
            assert p.health_check() is True

    def test_missing_ollama_package(self):
        from nexarq_cli.llm.ollama import OllamaProvider
        p = OllamaProvider()
        with patch.dict("sys.modules", {"ollama": None}):
            with pytest.raises(RuntimeError, match="ollama package"):
                p._call_api("test prompt")


# ── LLMFactory ────────────────────────────────────────────────────────────────

class TestLLMFactory:
    def _make_factory(self, provider_name="ollama", model="codellama"):
        cfg = NexarqConfig()
        cfg.providers["default"] = ProviderConfig(name=ProviderName(provider_name), model=model)
        secrets = SecretsManager()
        return LLMFactory(cfg, secrets)

    def test_builds_ollama_provider(self):
        from nexarq_cli.llm.ollama import OllamaProvider
        factory = self._make_factory("ollama")
        provider = factory.get("default")
        assert isinstance(provider, OllamaProvider)

    def test_caches_provider_instance(self):
        factory = self._make_factory()
        p1 = factory.get("default")
        p2 = factory.get("default")
        assert p1 is p2

    def test_invalidate_clears_cache(self):
        factory = self._make_factory()
        p1 = factory.get("default")
        factory.invalidate("default")
        p2 = factory.get("default")
        assert p1 is not p2

    def test_invalidate_all_clears_cache(self):
        factory = self._make_factory()
        factory.get("default")
        factory.invalidate()
        assert factory._cache == {}

    def test_cloud_provider_without_key_raises(self):
        cfg = NexarqConfig()
        cfg.providers["default"] = ProviderConfig(name=ProviderName.OPENAI, model="gpt-4o")
        secrets = SecretsManager()
        with patch.object(secrets, "get_key", return_value=None):
            factory = LLMFactory(cfg, secrets)
            with pytest.raises(RuntimeError, match="No API key"):
                factory.get("default")

    def test_fallback_provider_used_on_failure(self):
        from nexarq_cli.llm.ollama import OllamaProvider
        cfg = NexarqConfig()
        cfg.providers["default"] = ProviderConfig(
            name=ProviderName.OPENAI,
            model="gpt-4o",
            fallback=ProviderName.OLLAMA,
        )
        cfg.providers["ollama"] = ProviderConfig(name=ProviderName.OLLAMA, model="codellama")
        secrets = SecretsManager()
        with patch.object(secrets, "get_key", return_value=None):
            factory = LLMFactory(cfg, secrets)
            provider = factory.get("default")
            assert isinstance(provider, OllamaProvider)

    def test_get_for_agent_resolves_correct_provider(self):
        from nexarq_cli.llm.ollama import OllamaProvider
        cfg = NexarqConfig()
        factory = LLMFactory(cfg, SecretsManager())
        provider = factory.get_for_agent("security")
        assert isinstance(provider, OllamaProvider)

    def test_cloud_provider_without_key_raises(self):
        """Factory raises RuntimeError when a cloud provider has no API key configured."""
        cfg = NexarqConfig()
        cfg.providers["default"] = ProviderConfig(name=ProviderName.OPENAI)
        factory = LLMFactory(cfg, SecretsManager())
        with pytest.raises(RuntimeError, match="No API key"):
            factory.get("default")


# ── BaseLLMProvider retry ─────────────────────────────────────────────────────

class TestBaseLLMProviderRetry:
    def test_complete_returns_response(self):
        p = _FakeProvider(model="m")
        r = p.complete("hello")
        assert r.text == "fake response"
        assert r.latency_ms >= 0

    def test_complete_sets_latency(self):
        p = _FakeProvider(model="m")
        r = p.complete("hello")
        assert r.latency_ms >= 0
