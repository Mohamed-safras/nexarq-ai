"""Architecture agent – SOLID, design patterns, coupling."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a software architect specializing in clean architecture and design patterns.

Review the following {language} code diff for architectural concerns:
- Single Responsibility Principle (SRP) violations
- Open/Closed Principle (OCP) violations
- Liskov Substitution Principle (LSP) violations
- Interface Segregation Principle (ISP) violations
- Dependency Inversion Principle (DIP) violations
- High coupling between modules (inappropriate intimacy)
- Missing or misapplied design patterns
- Circular dependencies
- Violation of layered architecture boundaries
- Anemic domain model or god objects

For each concern:
  PRINCIPLE: <which principle or pattern>
  LOCATION: <code snippet>
  PROBLEM: <description>
  RECOMMENDATION: <suggested restructuring>

If architecture is sound: "No architectural issues found."

Code diff:
```{language}
{diff}
```"""


class ArchitectureAgent(BaseAgent):
    name = "architecture"
    description = "SOLID principles, design patterns, coupling analysis"
    severity = Severity.MEDIUM
    needs_tools = True  # navigates module structure to evaluate coupling/cohesion

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=False, read_full_repo=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
