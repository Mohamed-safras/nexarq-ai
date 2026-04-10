"""Abstract base class for all LLM providers."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    cached: bool = False
    metadata: dict = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class BaseLLMProvider(ABC):
    """
    Common interface for every LLM backend.

    Subclasses implement `_call_api` and `_call_api_async`.
    The base class handles timing, retries (via tenacity), and
    response wrapping.
    """

    name: str = "base"

    def __init__(
        self,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: int = 120,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    # ── public ───────────────────────────────────────────────────────────────

    def complete(self, prompt: str, system: str = "") -> LLMResponse:
        """Synchronous completion with timing."""
        t0 = time.monotonic()
        response = self._complete_with_retry(prompt, system)
        response.latency_ms = (time.monotonic() - t0) * 1000
        return response

    async def acomplete(self, prompt: str, system: str = "") -> LLMResponse:
        """Async completion."""
        import asyncio

        t0 = time.monotonic()
        response = await asyncio.get_event_loop().run_in_executor(
            None, self.complete, prompt, system
        )
        response.latency_ms = (time.monotonic() - t0) * 1000
        return response

    def stream(self, prompt: str, system: str = ""):
        """
        Stream tokens from the provider as they arrive (SRS 3.8).

        Yields str chunks. Falls back to a single-chunk yield if the
        provider does not implement `_stream_api`.
        """
        try:
            yield from self._stream_api(prompt, system)
        except Exception:
            response = self.complete(prompt, system)
            yield response.text

    def _stream_api(self, prompt: str, system: str):
        """
        Provider-specific streaming implementation.

        Yields str chunks. Subclasses override this to enable real streaming.
        Default: raises NotImplementedError (falls back to complete()).
        """
        raise NotImplementedError

    # ── internal ─────────────────────────────────────────────────────────────

    def _complete_with_retry(self, prompt: str, system: str) -> LLMResponse:
        """Wrap _call_api with tenacity retries."""
        try:
            from tenacity import retry, stop_after_attempt, wait_exponential

            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=2, max=30),
                reraise=True,
            )
            def _inner():
                return self._call_api(prompt, system)

            return _inner()
        except ImportError:
            return self._call_api(prompt, system)

    @abstractmethod
    def _call_api(self, prompt: str, system: str) -> LLMResponse:
        """Provider-specific API call. Must return LLMResponse."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the provider is reachable and functional."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model!r})"
