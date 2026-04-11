import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt } from '../agent-template.ts'

const instructions = `Assess the overall risk level of this diff and produce a risk score.

Evaluate:
- Size and scope (how many files and lines changed)
- Presence of security-sensitive changes (auth, crypto, permissions)
- Database or schema changes
- Public API surface changes (breaking vs additive)
- Test coverage of the changed code
- Deployment risk (infrastructure changes, config changes)

Output format:
RISK SCORE: [LOW | MEDIUM | HIGH | CRITICAL]
CONFIDENCE: [0–100]%

RISK FACTORS:
- <factor 1>
- <factor 2>
...

SUMMARY: One sentence overall assessment.`

export const riskScoringAgent: AgentDefinition = {
  name: 'risk_scoring',
  displayName: 'Risk Scoring',
  description: 'Overall risk assessment and deployment safety score',
  severity: 'info',
  tier: 2,
  needsTools: false,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
}
