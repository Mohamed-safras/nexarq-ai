"""API design agent – REST conventions, versioning, contracts."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a senior API design expert with deep knowledge of REST, GraphQL, and RPC.

Review the following {language} code diff for API design quality:
- Incorrect HTTP method usage (GET with side-effects, POST for idempotent ops)
- Missing or incorrect HTTP status codes
- Inconsistent URL naming (mixing plural/singular, camelCase/kebab-case)
- Missing input validation and sanitization at API boundaries
- Sensitive data exposed in response payloads (passwords, internal IDs)
- Missing rate limiting or throttling considerations
- Missing pagination for list endpoints
- Breaking API contract changes without versioning
- Missing or incorrect Content-Type handling
- CORS misconfiguration

For each issue:
  SEVERITY: [HIGH|MEDIUM|LOW]
  ENDPOINT/FUNCTION: <location>
  ISSUE: <description>
  FIX: <corrected approach>

If API design is correct: "API design follows best practices."

Code diff:
```{language}
{diff}
```"""


class APIDesignAgent(BaseAgent):
    name = "api_design"
    description = "REST conventions, status codes, contract violations"
    severity = Severity.MEDIUM

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
