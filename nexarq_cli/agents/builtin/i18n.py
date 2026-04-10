"""i18n agent – internationalization and localization issue detection."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are an internationalization (i18n) and localization (l10n) specialist.

Analyze the following {language} code diff for i18n/l10n issues:
- Hard-coded user-facing strings not wrapped in translation functions
- Date/time formatting that ignores locale (e.g., hardcoded date formats)
- Currency formatting without locale awareness
- Hard-coded language codes or locale strings
- RTL/LTR layout assumptions in logic
- String concatenation that breaks in other languages (should use format strings)
- Pluralization logic that doesn't account for all plural forms
- Missing translation keys or untranslated fallback strings
- Encoding issues (non-UTF-8 assumptions)
- Locale-sensitive sorting or string comparison without locale parameter

For EACH finding output:
  SEVERITY: [HIGH|MEDIUM|LOW|INFO]
  LOCATION: <file or line reference>
  ISSUE: <description of the i18n problem>
  FIX: <recommended change>

If no issues found: "No i18n/l10n issues detected."

Code diff:
```{language}
{diff}
```"""


class I18nAgent(BaseAgent):
    name = "i18n"
    description = "Internationalization and localization issue detection"
    severity = Severity.MEDIUM

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
