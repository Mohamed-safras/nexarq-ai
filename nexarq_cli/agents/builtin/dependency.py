"""Dependency analysis agent – vulnerable packages, license issues, bloat."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a dependency and supply-chain security expert.

Analyze the following code diff for dependency-related concerns:
- New imports of packages that are known to have security issues
- Overly broad version pinning (e.g., >=1.0.0 with no upper bound)
- Missing version pinning in requirements/package.json
- Direct use of packages that have better maintained alternatives
- Packages imported but never used
- Circular import patterns that indicate poor module design
- Use of deprecated APIs from dependencies
- License compatibility concerns for new packages
- Development dependencies mixed with production dependencies

For each finding:
  SEVERITY: [HIGH|MEDIUM|LOW]
  PACKAGE: <package name>
  CONCERN: <description>
  RECOMMENDATION: <action to take>

If no dependency issues: "Dependencies appear healthy."

Code diff:
```{language}
{diff}
```"""


class DependencyAgent(BaseAgent):
    name = "dependency"
    description = "Vulnerable packages, version pinning, license issues"
    severity = Severity.HIGH

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
