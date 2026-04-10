"""Data redaction before sending to cloud providers (SEC-6, PR-7)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class RedactionResult:
    text: str
    redacted_count: int
    patterns_matched: list[str] = field(default_factory=list)


# Built-in sensitive patterns
_DEFAULT_PATTERNS: list[tuple[str, str]] = [
    # API keys / tokens / secrets in assignments
    (
        r'(?i)(api[_\-]?key|secret[_\-]?key|access[_\-]?token|auth[_\-]?token'
        r'|password|passwd|credential|private[_\-]?key)\s*[=:]\s*["\']?[\w\-./+]{8,}["\']?',
        "<REDACTED_CREDENTIAL>",
    ),
    # Bearer tokens
    (r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*", "bearer <REDACTED_TOKEN>"),
    # AWS key patterns
    (r"(?i)(AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}", "<REDACTED_AWS_KEY>"),
    # Private key blocks
    (r"-----BEGIN\s+[\w ]+PRIVATE KEY-----[\s\S]*?-----END\s+[\w ]+PRIVATE KEY-----",
     "<REDACTED_PRIVATE_KEY>"),
    # Generic high-entropy strings that look like secrets (hex/base64, 32+ chars)
    (r'(?<=["\' =])[A-Za-z0-9+/]{32,}={0,2}(?=["\' \n])', "<REDACTED_SECRET>"),
    # Connection strings with passwords
    (r"(?i)(postgres|mysql|mongodb|redis|amqp)://[^:]+:[^@]+@", r"\1://<REDACTED>@"),
]


class Redactor:
    """Apply redaction patterns to text before it leaves the machine."""

    def __init__(self, extra_patterns: list[str] | None = None) -> None:
        self._compiled: list[tuple[re.Pattern, str]] = []

        for pattern, replacement in _DEFAULT_PATTERNS:
            self._compiled.append((re.compile(pattern), replacement))

        # User-supplied custom patterns (from config)
        for pattern in (extra_patterns or []):
            self._compiled.append((re.compile(pattern), "<REDACTED>"))

    def redact(self, text: str) -> RedactionResult:
        """Return redacted text and metadata."""
        result = text
        total = 0
        matched: list[str] = []

        for regex, replacement in self._compiled:
            new_result, n = regex.subn(replacement, result)
            if n:
                total += n
                matched.append(regex.pattern[:60])
            result = new_result

        return RedactionResult(
            text=result,
            redacted_count=total,
            patterns_matched=matched,
        )

    def is_safe(self, text: str) -> bool:
        """Quick check: returns True if no sensitive data found."""
        return self.redact(text).redacted_count == 0
