import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt } from '../agent-template.ts'

const instructions = `Focus ONLY on compliance and regulatory concerns in this diff.

Check for:
- GDPR: collecting or processing personal data without consent mechanisms
- GDPR: missing right-to-deletion pathways for user data
- HIPAA: PHI (Protected Health Information) handled without required encryption or access controls
- PCI-DSS: card numbers or CVVs stored or logged
- License violations (using GPL code in a proprietary project, for example)
- Missing audit trails for sensitive operations
- Cookie/tracking code without consent checks`

export const complianceAgent: AgentDefinition = {
  name: 'compliance',
  displayName: 'Compliance',
  description: 'GDPR, HIPAA, PCI-DSS, and license compliance issues',
  severity: 'high',
  tier: 2,
  needsTools: false,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
}
