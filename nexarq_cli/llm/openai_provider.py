"""OpenAI cloud LLM provider."""
from __future__ import annotations

from nexarq_cli.llm.base import BaseLLMProvider, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """Uses OpenAI chat completions API."""

    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: int = 120,
    ) -> None:
        super().__init__(model, temperature, max_tokens, timeout)
        self._api_key = api_key

    def _call_api(self, prompt: str, system: str = "") -> LLMResponse:
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

        client = OpenAI(api_key=self._api_key, timeout=self.timeout)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        return LLMResponse(
            text=resp.choices[0].message.content or "",
            provider=self.name,
            model=self.model,
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
        )

    def _stream_api(self, prompt: str, system: str = ""):
        """Real-time token streaming via OpenAI (SRS 3.8)."""
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package not installed.")

        client = OpenAI(api_key=self._api_key, timeout=self.timeout)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        with client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        ) as stream:
            for chunk in stream:
                token = chunk.choices[0].delta.content if chunk.choices else None
                if token:
                    yield token

    def health_check(self) -> bool:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self._api_key, timeout=5)
            client.models.list()
            return True
        except Exception:
            return False
