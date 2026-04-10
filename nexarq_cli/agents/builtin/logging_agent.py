"""Logging agent – log level usage, PII in logs, structured logging."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a logging and observability expert.

Analyze the following {language} code diff for logging quality:
- Personal Identifiable Information (PII) logged (names, emails, passwords, tokens)
- Secrets or credentials in log messages
- Missing logging for critical operations (auth events, data mutations)
- Wrong log level usage (debug in production, error for expected conditions)
- Unstructured logging where structured (JSON) logging should be used
- Log messages without context (no request ID, user ID, correlation ID)
- print() statements left in production code instead of proper logging
- Missing log rotation or size limits configuration
- Excessive logging that could impact performance
- Missing audit trail for compliance-sensitive operations

For each issue:
  SEVERITY: [CRITICAL|HIGH|MEDIUM|LOW]
  LOCATION: <code snippet>
  ISSUE: <description>
  FIX: <corrected logging>

If logging is correct: "Logging practices look appropriate."

Code diff:
```{language}
{diff}
```"""


class LoggingAgent(BaseAgent):
    name = "logging"
    description = "PII in logs, log levels, structured logging, audit trail"
    severity = Severity.HIGH

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
