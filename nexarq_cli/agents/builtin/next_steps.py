"""
Next Steps agent — synthesises all review findings into a concrete action plan.

Unlike other agents that analyse specific aspects of the diff, this agent reads
the compiled outputs from all other agents (passed via context["_agent_results"])
and produces a prioritised, actionable "What to do next" list with specific
file references and code suggestions.
"""
from __future__ import annotations

from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You have received the full output from a multi-agent automated code review.
Your task is to produce a clear, actionable "What to do next" plan for the developer.

LANGUAGE: {language}

CHANGED FILES:
{changed_files}

CODEBASE CONTEXT:
{codebase_context}

ALL AGENT FINDINGS:
{agent_results}

---

Produce a structured action plan following this EXACT format:

WHAT TO DO NEXT
===============

### CRITICAL (fix before merge)
- [ ] <specific action> — <file>:<line if known>
      <one-line explanation of why>
      <concrete code suggestion if applicable>

### HIGH (fix soon)
- [ ] <specific action> — <file>
      <one-line explanation>

### MEDIUM (address in follow-up)
- [ ] <specific action>

### TESTING CHECKLIST
- [ ] <what to test / verify>

### QUICK WINS (< 5 minutes each)
- [ ] <simple improvement>

---

RULES:
- Be SPECIFIC: name exact files, functions, line numbers when known
- Be ACTIONABLE: every item must be something the developer can do right now
- Be CONCISE: max 2 lines per item
- If NO issues in a severity level, omit that section entirely
- Do NOT repeat findings — synthesise them into one actionable list
- When suggesting code, show the fix inline (not a separate block)
- Order items by impact within each section (most impactful first)
- Only include items that are genuinely actionable from the review findings
"""


class NextStepsAgent(BaseAgent):
    name = "next_steps"
    description = "Synthesises all review findings into a prioritised action plan"
    severity = Severity.INFO

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=False)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        ctx = context or {}

        agent_results = ctx.get("_agent_results", "No agent results available.")
        codebase_context = ctx.get("_codebase_context", "Not available.")
        changed_files = ctx.get("_changed_files", "Unknown")

        # Truncate codebase context to keep prompt manageable
        if len(codebase_context) > 3000:
            codebase_context = codebase_context[:3000] + "\n... (truncated)"

        return _PROMPT.format(
            language=language,
            changed_files=changed_files,
            codebase_context=codebase_context,
            agent_results=agent_results,
        )
