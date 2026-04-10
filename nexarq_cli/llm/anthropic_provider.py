"""Anthropic Claude cloud LLM provider."""
from __future__ import annotations

from nexarq_cli.llm.base import BaseLLMProvider, LLMResponse


class AnthropicProvider(BaseLLMProvider):
    """Uses Anthropic Messages API."""

    name = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: int = 120,
    ) -> None:
        super().__init__(model, temperature, max_tokens, timeout)
        self._api_key = api_key

    def _call_api(self, prompt: str, system: str = "") -> LLMResponse:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError(
                "anthropic package not installed. Run: pip install anthropic"
            )

        client = anthropic.Anthropic(api_key=self._api_key, timeout=self.timeout)

        kwargs: dict = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system

        resp = client.messages.create(**kwargs)

        text = "".join(
            block.text for block in resp.content if hasattr(block, "text")
        )

        return LLMResponse(
            text=text,
            provider=self.name,
            model=self.model,
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
        )

    def _stream_api(self, prompt: str, system: str = ""):
        """Real-time token streaming via Anthropic (SRS 3.8)."""
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed.")

        client = anthropic.Anthropic(api_key=self._api_key, timeout=self.timeout)
        kwargs: dict = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system

        with client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                if text:
                    yield text

    def health_check(self) -> bool:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self._api_key, timeout=5)
            client.models.list()
            return True
        except Exception:
            return False
