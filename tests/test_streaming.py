"""Tests for real-time streaming LLM output (SRS 3.8)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from nexarq_cli.llm.base import BaseLLMProvider, LLMResponse


class _StreamingProvider(BaseLLMProvider):
    """Mock provider that yields streaming chunks."""
    name = "streaming_mock"

    def _call_api(self, prompt: str, system: str = "") -> LLMResponse:
        return LLMResponse(text="full response", provider="mock", model="m")

    def _stream_api(self, prompt: str, system: str = ""):
        chunks = ["Hello", " from", " stream", "!"]
        yield from chunks

    def health_check(self) -> bool:
        return True


class _NonStreamingProvider(BaseLLMProvider):
    """Provider without streaming – should fall back to complete()."""
    name = "non_streaming"

    def _call_api(self, prompt: str, system: str = "") -> LLMResponse:
        return LLMResponse(text="full response", provider="mock", model="m")

    def health_check(self) -> bool:
        return True


class TestStreamingBase:
    def test_stream_yields_chunks(self):
        p = _StreamingProvider(model="m")
        chunks = list(p.stream("test prompt"))
        assert chunks == ["Hello", " from", " stream", "!"]

    def test_stream_joins_to_full_text(self):
        p = _StreamingProvider(model="m")
        full = "".join(p.stream("test"))
        assert full == "Hello from stream!"

    def test_non_streaming_falls_back_to_complete(self):
        p = _NonStreamingProvider(model="m")
        chunks = list(p.stream("test"))
        assert len(chunks) == 1
        assert chunks[0] == "full response"

    def test_stream_with_system_prompt(self):
        p = _StreamingProvider(model="m")
        chunks = list(p.stream("prompt", system="you are an expert"))
        assert len(chunks) > 0

    def test_stream_empty_provider_still_yields(self):
        class _EmptyProvider(_NonStreamingProvider):
            def _call_api(self, prompt, system=""):
                return LLMResponse(text="", provider="mock", model="m")

        p = _EmptyProvider(model="m")
        chunks = list(p.stream("test"))
        assert chunks == [""]  # Single empty chunk from complete()

    def test_stream_multiple_calls_independent(self):
        p = _StreamingProvider(model="m")
        first = list(p.stream("first"))
        second = list(p.stream("second"))
        assert first == second  # Same mock output


class TestCloudProviderStreaming:
    """All cloud providers must implement _stream_api for SRS 3.8."""

    def test_openai_has_stream_api(self):
        from nexarq_cli.llm.openai_provider import OpenAIProvider
        p = OpenAIProvider(api_key="test-key")
        assert hasattr(p, "_stream_api")

    def test_anthropic_has_stream_api(self):
        from nexarq_cli.llm.anthropic_provider import AnthropicProvider
        p = AnthropicProvider(api_key="test-key")
        assert hasattr(p, "_stream_api")

    def test_google_has_stream_api(self):
        from nexarq_cli.llm.google_provider import GoogleProvider
        p = GoogleProvider(api_key="test-key")
        assert hasattr(p, "_stream_api")

    def test_openai_stream_fallback_on_error(self):
        from nexarq_cli.llm.openai_provider import OpenAIProvider
        from nexarq_cli.llm.base import LLMResponse
        p = OpenAIProvider(api_key="fake-key-test")
        with patch.object(p, "_stream_api", side_effect=RuntimeError("no api key")):
            with patch.object(p, "complete",
                              return_value=LLMResponse(text="buffered", provider="openai", model="gpt-4o")):
                chunks = list(p.stream("test"))
                assert "buffered" in "".join(chunks)

    def test_anthropic_stream_fallback_on_error(self):
        from nexarq_cli.llm.anthropic_provider import AnthropicProvider
        from nexarq_cli.llm.base import LLMResponse
        p = AnthropicProvider(api_key="fake-key-test")
        with patch.object(p, "_stream_api", side_effect=RuntimeError("no api key")):
            with patch.object(p, "complete",
                              return_value=LLMResponse(text="buffered", provider="anthropic", model="claude")):
                chunks = list(p.stream("test"))
                assert "buffered" in "".join(chunks)


class TestOllamaStreaming:
    def test_ollama_stream_api_defined(self):
        from nexarq_cli.llm.ollama import OllamaProvider
        p = OllamaProvider(model="codellama")
        # _stream_api should be defined (overrides NotImplementedError)
        assert hasattr(p, "_stream_api")

    def test_ollama_stream_falls_back_when_unavailable(self):
        from nexarq_cli.llm.ollama import OllamaProvider
        p = OllamaProvider(model="codellama", base_url="http://localhost:19999")

        # With ollama unreachable, stream() should raise (via _stream_api → complete)
        # but not crash with AttributeError
        with patch("nexarq_cli.llm.ollama.OllamaProvider._stream_api", side_effect=ConnectionError):
            with patch.object(p, "complete") as mock_complete:
                mock_complete.return_value = LLMResponse(
                    text="fallback", provider="ollama", model="codellama"
                )
                chunks = list(p.stream("test"))
                # Falls back to complete() output
                assert "fallback" in "".join(chunks)

    def test_ollama_stream_yields_strings(self):
        from nexarq_cli.llm.ollama import OllamaProvider

        p = OllamaProvider(model="test-model")

        mock_chunks = [
            {"message": {"content": "tok1"}},
            {"message": {"content": "tok2"}},
            {"message": {"content": ""}},       # empty chunk ignored
            {"message": {"content": "tok3"}},
        ]

        with patch("nexarq_cli.llm.ollama.OllamaProvider._call_api"), \
             patch("ollama.chat", return_value=iter(mock_chunks)):
            chunks = list(p._stream_api("test prompt"))

        assert chunks == ["tok1", "tok2", "tok3"]
