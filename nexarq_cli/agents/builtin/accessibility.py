"""Accessibility agent – WCAG compliance, ARIA, semantic HTML."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a web accessibility expert with WCAG 2.1 AA certification.

Review the following code diff for accessibility issues:
- Missing alt text on images
- Missing ARIA labels on interactive elements
- Non-semantic HTML (div/span used instead of button, nav, main, etc.)
- Color contrast violations (insufficient contrast ratios)
- Missing keyboard navigation support (tabIndex, onKeyDown)
- Missing focus management in modals or dynamic content
- Form inputs without associated labels
- Missing skip-navigation links for screen readers
- Inaccessible error messages (errors not announced to screen readers)
- Time-based content without pause/stop controls

For each issue:
  WCAG CRITERION: <e.g. 1.1.1 Non-text Content>
  SEVERITY: [HIGH|MEDIUM|LOW]
  LOCATION: <code snippet>
  ISSUE: <description>
  FIX: <accessible version>

If no issues: "No accessibility violations found."

Code diff:
```{language}
{diff}
```"""


class AccessibilityAgent(BaseAgent):
    name = "accessibility"
    description = "WCAG 2.1, ARIA, semantic HTML, keyboard navigation"
    severity = Severity.MEDIUM

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
