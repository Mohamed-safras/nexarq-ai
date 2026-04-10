"""Error handling agent – exception patterns, recovery, logging."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are an error handling and resilience engineering expert.

Review the following {language} code diff for error handling quality:
- Bare except/catch clauses that swallow all exceptions
- Exceptions caught but not logged or re-raised appropriately
- Missing error handling for I/O operations (file, network, DB)
- Exception messages that expose internal details to end users
- Missing cleanup in finally blocks (resources not released)
- Catching and ignoring specific exceptions silently
- Using exceptions for normal control flow (anti-pattern)
- Missing timeout handling for external calls
- Retry logic without exponential backoff or jitter
- Error responses that don't include a useful error code

For each issue:
  SEVERITY: [HIGH|MEDIUM|LOW]
  LOCATION: <code snippet>
  ISSUE: <description>
  FIX: <improved error handling code>

If error handling is robust: "Error handling appears well-designed."

Code diff:
```{language}
{diff}
```"""


class ErrorHandlingAgent(BaseAgent):
    name = "error_handling"
    description = "Exception patterns, swallowed errors, missing cleanup"
    severity = Severity.HIGH

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
