"""Risk scoring agent – overall change risk assessment."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a senior software engineering risk analyst.

Analyze the following {language} code diff and produce a comprehensive RISK SCORE REPORT.

Assess these risk dimensions (score 1-10 each):
1. Security Risk     – likelihood of security vulnerability introduction
2. Reliability Risk  – chance of runtime errors, crashes, data corruption
3. Performance Risk  – potential performance regressions
4. Maintainability   – long-term code health impact
5. Test Coverage     – adequacy of tests for the changes
6. Breaking Change   – risk of breaking existing functionality/API contracts
7. Complexity        – cognitive load increase

Rules:
- Overall Risk Score = average of the 7 dimension scores (rounded to 1 decimal)
- Deploy Recommendation: write exactly ONE word — SAFE, CAUTION, or BLOCK
  - SAFE   = overall score 1-3
  - CAUTION = overall score 4-6
  - BLOCK  = overall score 7-10

OUTPUT FORMAT (fill in every X with a real number):
```
RISK ASSESSMENT

Overall Risk Score: X/10

Dimension Scores:
  Security Risk:      X/10
  Reliability Risk:   X/10
  Performance Risk:   X/10
  Maintainability:    X/10
  Test Coverage:      X/10
  Breaking Change:    X/10
  Complexity:         X/10

Key Risk Factors:
  - <specific finding from the diff>
  - <specific finding from the diff>

Risk Mitigation:
  1. <concrete action>
  2. <concrete action>

Deploy Recommendation: SAFE
Reason: <one sentence>
```

Code diff to assess:
```{language}
{diff}
```"""


class RiskScoringAgent(BaseAgent):
    name = "risk_scoring"
    description = "Overall change risk assessment with multi-dimension scoring"
    severity = Severity.HIGH

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
