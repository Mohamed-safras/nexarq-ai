"""Explain agent – plain-English walkthrough of the diff."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a code teacher helping a developer understand a code change.

Explain the following {language} code diff clearly:

1. SUMMARY (2-3 sentences): What does this change do overall?
2. CHANGES WALKTHROUGH: Go through each changed section and explain:
   - What existed before
   - What it was changed to
   - Why this change is likely being made
3. KEY CONCEPTS: What patterns, algorithms, or frameworks are introduced?
4. IMPACT: What parts of the system does this change affect?
5. DEPENDENCIES: Any new dependencies introduced and what they provide?

Keep the explanation accessible to a developer unfamiliar with this codebase.

Code diff:
```{language}
{diff}
```"""


class ExplainAgent(BaseAgent):
    name = "explain"
    description = "Plain-English walkthrough of the code change"
    severity = Severity.INFO

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
