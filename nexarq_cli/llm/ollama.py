"""Ollama local LLM provider."""
from __future__ import annotations

import os

from nexarq_cli.llm.base import BaseLLMProvider, LLMResponse

DEFAULT_URL = os.environ.get("NEXARQ_OLLAMA_URL", "http://localhost:11434")


class OllamaProvider(BaseLLMProvider):
    """Runs models locally via Ollama – no data leaves the machine."""

    name = "ollama"

    def __init__(
        self,
        model: str = "codellama",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: int = 120,
        base_url: str = DEFAULT_URL,
    ) -> None:
        super().__init__(model, temperature, max_tokens, timeout)
        self.base_url = base_url.rstrip("/")

    def _call_api(self, prompt: str, system: str = "") -> LLMResponse:
        try:
            import ollama as _ollama
        except ImportError:
            raise RuntimeError(
                "ollama package not installed. Run: pip install ollama"
            )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = _ollama.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        )

        content = response["message"]["content"]

        # Ollama returns token counts at top level, not inside "usage"
        return LLMResponse(
            text=content,
            provider=self.name,
            model=self.model,
            prompt_tokens=response.get("prompt_eval_count", 0),
            completion_tokens=response.get("eval_count", 0),
        )

    def _stream_api(self, prompt: str, system: str = ""):
        """Real-time streaming via Ollama (SRS 3.8)."""
        try:
            import ollama as _ollama
        except ImportError:
            raise RuntimeError("ollama package not installed. Run: pip install ollama")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        for chunk in _ollama.chat(
            model=self.model,
            messages=messages,
            stream=True,
            options={"temperature": self.temperature, "num_predict": self.max_tokens},
        ):
            token = chunk.get("message", {}).get("content", "")
            if token:
                yield token

    def health_check(self) -> bool:
        try:
            import httpx
            r = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            return r.status_code == 200
        except Exception:
            return False
