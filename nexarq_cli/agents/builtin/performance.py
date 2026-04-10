"""Performance agent – inefficiencies, complexity, memory usage."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a performance engineering expert.

Analyze the following {language} code diff for performance issues:
- Algorithmic complexity (O(n²) or worse where O(n) is achievable)
- Unnecessary database queries inside loops (N+1 problems)
- Missing indexes or unoptimised query patterns
- Excessive memory allocations and copies
- Blocking I/O in async contexts
- Redundant computations that should be cached or memoized
- Large data structures loaded entirely into memory
- Inefficient string concatenation in loops
- Missing pagination for large result sets
- Unoptimised imports or module loading

For each issue:
  IMPACT: [HIGH|MEDIUM|LOW]
  LOCATION: <code snippet>
  PROBLEM: <description>
  OPTIMIZED VERSION: <improved code>
  EXPECTED GAIN: <estimated improvement>

If no issues: "No performance issues found."

Code diff:
```{language}
{diff}
```"""


class PerformanceAgent(BaseAgent):
    name = "performance"
    description = "Complexity, N+1 queries, memory, blocking I/O"
    severity = Severity.HIGH

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
