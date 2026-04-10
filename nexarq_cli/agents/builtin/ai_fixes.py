"""AI fixes agent – generate concrete, applicable fix suggestions."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are an expert software engineer. Your task is to generate CONCRETE, APPLICABLE fixes
for problems found in the following code diff.

Analyze the diff for the most impactful issues, then provide ready-to-apply fixes.

For EACH fix:
1. Identify the issue clearly
2. Provide the EXACT replacement code
3. Explain why this fix is correct

OUTPUT FORMAT per fix:
```
FIX #N: <issue title>
Severity: [CRITICAL|HIGH|MEDIUM|LOW]
File: <filename if determinable>
Issue: <clear description of the problem>

Before:
```{language}
<original problematic code>
```

After:
```{language}
<fixed code>
```

Why: <explanation of why this fix is correct and safe>
```

Limit output to the 5 most impactful fixes.
Focus on: security vulnerabilities > bugs > performance > style.
Generate ONLY fixes for clear, unambiguous issues.

If the diff has no clear issues to fix: "No automatic fixes suggested – code looks correct."

Code diff to analyze and fix:
```{language}
{diff}
```"""


class AIFixesAgent(BaseAgent):
    name = "ai_fixes"
    description = "Generate concrete, applicable code fixes with before/after diffs"
    severity = Severity.HIGH

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
