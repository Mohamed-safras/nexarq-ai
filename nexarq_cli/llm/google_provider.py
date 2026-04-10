"""Google Gemini cloud LLM provider (google-genai SDK)."""
from __future__ import annotations

from nexarq_cli.llm.base import BaseLLMProvider, LLMResponse


class GoogleProvider(BaseLLMProvider):
    """Uses the Google Gemini API via the google-genai SDK."""

    name = "google"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-pro",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: int = 120,
    ) -> None:
        super().__init__(model, temperature, max_tokens, timeout)
        self._api_key = api_key

    def _call_api(self, prompt: str, system: str = "") -> LLMResponse:
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise RuntimeError(
                "google-genai not installed. Run: pip install google-genai"
            )

        client = genai.Client(api_key=self._api_key)
        contents = f"{system}\n\n{prompt}" if system else prompt

        resp = client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            ),
        )

        return LLMResponse(
            text=resp.text or "",
            provider=self.name,
            model=self.model,
            prompt_tokens=getattr(resp.usage_metadata, "prompt_token_count", 0),
            completion_tokens=getattr(resp.usage_metadata, "candidates_token_count", 0),
        )

    def _stream_api(self, prompt: str, system: str = ""):
        """Real-time token streaming via Google Gemini (SRS 3.8)."""
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise RuntimeError("google-genai not installed.")

        client = genai.Client(api_key=self._api_key)
        contents = f"{system}\n\n{prompt}" if system else prompt

        for chunk in client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            ),
        ):
            text = getattr(chunk, "text", None)
            if text:
                yield text

    def health_check(self) -> bool:
        try:
            from google import genai
            client = genai.Client(api_key=self._api_key)
            next(iter(client.models.list()), None)
            return True
        except Exception:
            return False
