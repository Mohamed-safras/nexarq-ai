"""LLM output validation and prompt injection prevention (SEC-10/11/12)."""
from __future__ import annotations

import re
from dataclasses import dataclass


# Patterns that indicate likely prompt injection in LLM responses
_INJECTION_PATTERNS: list[str] = [
    r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"(?i)you\s+are\s+now\s+(an?\s+)?(?!a\s+code)",
    r"(?i)disregard\s+your\s+(previous|system)\s+prompt",
    r"(?i)act\s+as\s+(?!a\s+(code|security|software))",
    r"(?i)jailbreak",
    r"(?i)DAN\s+mode",
    r"(?i)pretend\s+(you\s+are|to\s+be)\s+(?!(a\s+)?(code|senior|expert))",
    r"SYSTEM\s*:",                   # Injected system tag
    r"<\|system\|>",
    r"<\|user\|>",
]

# Suspicious executable-like output patterns
_EXEC_PATTERNS: list[str] = [
    r"(?i)(subprocess|os\.system|exec|eval)\s*\(",
    r"(?i)__import__\s*\(",
    r"(?i)rm\s+-rf\s+/",
    r"(?i)curl\s+.+\|\s*(bash|sh)",
    r"(?i)wget\s+.+\|\s*(bash|sh)",
]


@dataclass
class ValidationResult:
    is_valid: bool
    warnings: list[str]
    sanitized_text: str


class OutputValidator:
    """Validate and sanitize LLM outputs before they are presented or acted on."""

    def __init__(self, strict: bool = False) -> None:
        self._strict = strict
        self._injection_re = [re.compile(p) for p in _INJECTION_PATTERNS]
        self._exec_re = [re.compile(p) for p in _EXEC_PATTERNS]

    def validate(self, text: str, context: str = "") -> ValidationResult:
        """
        Validate LLM output for injection signals and dangerous content.

        Args:
            text:    The raw LLM output.
            context: Optional description of the agent producing this output.

        Returns:
            ValidationResult with sanitized text and any warnings.
        """
        warnings: list[str] = []
        sanitized = text

        # Check for prompt injection attempts in the response
        for pattern in self._injection_re:
            if pattern.search(text):
                warnings.append(
                    f"Possible prompt injection detected [{pattern.pattern[:50]}]"
                )
                if self._strict:
                    sanitized = pattern.sub("[BLOCKED]", sanitized)

        # Check for executable shell/code patterns planted in response
        for pattern in self._exec_re:
            if pattern.search(text):
                warnings.append(
                    f"Suspicious executable pattern in output [{pattern.pattern[:50]}]"
                )

        # Enforce reasonable output size (prevent token-stuffing)
        max_chars = 100_000
        if len(text) > max_chars:
            warnings.append(f"Output truncated: exceeded {max_chars} characters.")
            sanitized = sanitized[:max_chars] + "\n\n[Output truncated by Nexarq]"

        is_valid = len(warnings) == 0 or not self._strict

        return ValidationResult(
            is_valid=is_valid,
            warnings=warnings,
            sanitized_text=sanitized,
        )

    def sanitize_prompt(self, user_input: str) -> str:
        """
        Strip injection-style strings from user-supplied data before
        embedding into an LLM prompt (SEC-10).
        """
        sanitized = user_input
        for pattern in self._injection_re:
            sanitized = pattern.sub("[FILTERED]", sanitized)
        return sanitized
