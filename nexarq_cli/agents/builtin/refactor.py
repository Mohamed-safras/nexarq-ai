"""Refactoring agent – DRY, complexity reduction, SOLID improvements."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a refactoring specialist.

Suggest concrete improvements for the following {language} code diff:
- Eliminate code duplication (DRY principle)
- Extract large functions into smaller, focused ones (< 20 lines ideal)
- Simplify complex conditionals using early returns or guard clauses
- Replace imperative loops with functional equivalents where clearer
- Remove unnecessary temporary variables
- Apply the Rule of Three (if duplicated 3+ times, extract)
- Reduce cognitive complexity below threshold of 10

For each suggestion:
  TYPE: [Extract|Simplify|DRY|Rename|Restructure]
  BEFORE: <original code>
  AFTER: <refactored code>
  BENEFIT: <why this is better>

If no improvements: "Code is well-structured. No refactoring needed."

Code diff:
```{language}
{diff}
```"""


class RefactorAgent(BaseAgent):
    name = "refactor"
    description = "DRY violations, complexity reduction, extract-method"
    severity = Severity.LOW

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
