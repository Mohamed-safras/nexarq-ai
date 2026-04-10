"""Style agent – code style, formatting, and naming convention analysis."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a code style and consistency expert.

Analyze the following {language} code diff for style issues, naming violations, and formatting problems.

STYLE DIMENSIONS TO CHECK:

Naming Conventions:
- Variables, functions, classes follow language conventions (snake_case, camelCase, PascalCase)
- Meaningful names (avoid single-letter vars except loop counters)
- Consistent naming across similar concepts
- Boolean names should be questions (is_, has_, can_, should_)

Formatting:
- Consistent indentation and spacing
- Line length adherence (typically 79-120 chars)
- Proper blank lines between sections
- Trailing whitespace

Code Organization:
- Import ordering and grouping
- Logical grouping of related code
- Constants at module/class level not inline
- Related functions/methods grouped together

Comments and Documentation:
- Outdated or misleading comments
- TODO/FIXME comments without ticket references
- Commented-out code that should be removed

{language}-specific conventions where applicable.

For EACH issue:
  CATEGORY: <naming|formatting|organization|comments>
  LOCATION: <reference>
  ISSUE: <what violates style>
  SUGGESTION: <corrected version>
  SEVERITY: [LOW|INFO]

If no style issues: "Code follows consistent style conventions."

Code diff:
```{language}
{diff}
```"""


class StyleAgent(BaseAgent):
    name = "style"
    description = "Code style, naming conventions, and formatting consistency"
    severity = Severity.LOW

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
