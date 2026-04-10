"""Maintainability agent – cyclomatic complexity, code smells."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a software maintainability and technical debt expert.

Analyze the following {language} code diff for maintainability concerns:
- Functions with cyclomatic complexity > 10 (too many branches)
- Functions longer than 50 lines (should be broken down)
- Deeply nested code (more than 3 levels of indentation)
- Inconsistent abstraction levels within a function
- Hard-coded values that will need to change (configuration, URLs, timeouts)
- Missing separation of concerns (business logic mixed with I/O)
- Premature optimisation that reduces readability
- Overly clever or obscure code that is hard to understand
- Missing or outdated comments for complex algorithms
- Technical debt markers (TODO, FIXME, HACK) without issue references

For each concern:
  IMPACT: [HIGH|MEDIUM|LOW]
  LOCATION: <code snippet>
  CONCERN: <description>
  IMPROVEMENT: <how to address it>

If code is maintainable: "Code maintainability looks good."

Code diff:
```{language}
{diff}
```"""


class MaintainabilityAgent(BaseAgent):
    name = "maintainability"
    description = "Cyclomatic complexity, code smells, technical debt"
    severity = Severity.MEDIUM

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
