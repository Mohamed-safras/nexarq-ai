"""Bug detection agent – logic errors, edge cases, exceptions."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are an expert bug hunter and QA engineer.

Scan the following {language} code diff for:
- Logic errors and off-by-one mistakes
- Unhandled exceptions and missing error handling
- Null / None dereferences
- Infinite loops or unbounded recursion
- Type mismatches and implicit conversions
- Race conditions and thread-safety issues
- Resource leaks (file handles, connections not closed)
- Incorrect boolean logic / De Morgan's law violations
- Integer overflow / underflow
- Incorrect operator precedence

For each bug:
  SEVERITY: [CRITICAL|HIGH|MEDIUM|LOW]
  LOCATION: <code snippet>
  CAUSE: <root cause explanation>
  FIX: <corrected code>

If no bugs found: "No bugs detected."

Code diff to analyze:
```{language}
{diff}
```"""


class BugsAgent(BaseAgent):
    name = "bugs"
    description = "Logic errors, edge cases, unhandled exceptions"
    severity = Severity.HIGH
    needs_tools = True  # reads full file context to understand call chains

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=False, read_full_repo=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
