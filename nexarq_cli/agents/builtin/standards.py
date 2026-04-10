"""Standards agent – project-specific rules (RAG-grounded)."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are enforcing project-specific coding standards.

Retrieved project standards (most relevant to the submitted code):
{standards}

Review the following {language} code diff ONLY against the standards listed above.

For each violation:
  RULE: <the exact standard violated>
  LOCATION: <code snippet>
  VIOLATION: <what is wrong>
  FIX: <compliant version>

If fully compliant: "No standards violations found."
DO NOT invent rules not present in the standards above.

Code diff:
```{language}
{diff}
```"""

_NO_STANDARDS = (
    "No project coding standards are configured. "
    "To enable this agent, run: nexarq config add-standards <path>"
)


class StandardsAgent(BaseAgent):
    name = "standards"
    description = "Project-specific coding rules (RAG-grounded)"
    severity = Severity.MEDIUM

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        standards = (context or {}).get("standards", "")
        if not standards:
            return f"SKIP: {_NO_STANDARDS}"
        return _PROMPT.format(language=language, diff=diff, standards=standards)

    def run(self, diff, language, provider, context=None):
        from nexarq_cli.agents.base import AgentResult
        standards = (context or {}).get("standards", "")
        if not standards:
            return AgentResult(
                agent_name=self.name,
                severity=self.severity,
                output=_NO_STANDARDS,
            )
        return super().run(diff, language, provider, context)
