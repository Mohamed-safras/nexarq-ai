"""Compliance agent – GDPR, HIPAA, SOC2 data handling patterns."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a compliance and data governance expert (GDPR, HIPAA, SOC2, PCI-DSS).

Review the following {language} code diff for compliance concerns:
- Personal data collected without clear purpose limitation (GDPR Art. 5)
- Missing data retention limits (data stored indefinitely)
- PHI (Protected Health Information) not encrypted at rest
- Payment card data (PAN, CVV) stored or logged (PCI-DSS violation)
- Missing consent mechanisms before data collection
- User data shared with third parties without disclosure
- Missing right-to-erasure implementation for user data
- Audit log tampering possible (logs are mutable)
- Missing data minimisation (collecting more data than needed)
- Cross-border data transfer without safeguards

For each finding:
  REGULATION: [GDPR|HIPAA|PCI-DSS|SOC2]
  SEVERITY: [CRITICAL|HIGH|MEDIUM|LOW]
  LOCATION: <code snippet>
  ISSUE: <compliance violation>
  REMEDIATION: <corrective action>

If compliant: "No compliance violations detected."

Code diff:
```{language}
{diff}
```"""


class ComplianceAgent(BaseAgent):
    name = "compliance"
    description = "GDPR, HIPAA, SOC2, PCI-DSS data handling patterns"
    severity = Severity.CRITICAL

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
