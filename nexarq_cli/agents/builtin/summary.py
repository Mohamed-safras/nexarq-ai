"""Summary agent – executive summary of the entire code change."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a principal software engineer reviewing a code change for an engineering leadership audience.

Analyze the following {language} code diff and produce a concise executive summary.

Your summary must cover:
1. WHAT changed – what functionality was added, modified, or removed
2. WHY it matters – business/technical impact of this change
3. QUALITY – overall assessment of code quality
4. CONCERNS – top 3 concerns (if any)
5. RECOMMENDATION – approve/request changes/block

OUTPUT FORMAT:
```
CHANGE SUMMARY
==============
What Changed:
  <1-3 sentences describing the change>

Technical Impact:
  <impact on system behaviour, APIs, performance, dependencies>

Quality Assessment: [EXCELLENT|GOOD|ACCEPTABLE|POOR]
  <brief quality note>

Top Concerns:
  1. <concern or "None">
  2. <concern or "None">
  3. <concern or "None">

Recommendation: [APPROVE|REQUEST CHANGES|BLOCK]
Reason: <brief rationale>
```

Code diff:
```{language}
{diff}
```"""


class SummaryAgent(BaseAgent):
    name = "summary"
    description = "Executive summary and overall change assessment"
    severity = Severity.INFO

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        ctx = context or {}
        # Include changed files list in the prompt for better summaries
        changed = ctx.get("_changed_files", "")
        change_type = ctx.get("_change_type", "")
        header = ""
        if changed or change_type:
            parts = []
            if change_type:
                parts.append(f"Change type: {change_type.replace('_', ' ')}")
            if changed:
                parts.append(f"Files changed:\n{changed}")
            header = "\n".join(parts) + "\n\n"
        return _PROMPT.format(language=language, diff=header + diff)
