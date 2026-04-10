"""Code review agent – style, naming, best practices."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a senior {language} engineer doing a thorough code review.

Review the following code diff for:
- Code style and readability (PEP8, language conventions)
- Naming conventions (variables, functions, classes, constants)
- Language-specific best practices and idioms
- Code organisation and structure
- Unnecessary complexity or verbosity
- Dead code, commented-out blocks, debug statements left in
- Magic numbers or strings that should be named constants
- Inconsistent formatting

For EVERY issue: quote the relevant lines, explain the problem, show the fix.
If nothing to report: "No style issues found."

Code diff:
```{language}
{diff}
```"""


class ReviewAgent(BaseAgent):
    name = "review"
    description = "Code style, naming conventions, best practices"
    severity = Severity.MEDIUM

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
