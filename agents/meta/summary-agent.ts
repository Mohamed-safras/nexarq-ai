import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt } from '../agent-template.ts'

const instructions = `Produce an executive summary of all review findings for this diff.

Your summary should:
- State the total count of findings by severity (CRITICAL, HIGH, MEDIUM, LOW)
- List the top 3 most important issues to fix before merging
- Give a one-line merge recommendation: BLOCK / CAUTION / APPROVE
- Keep the total summary under 200 words

Format:
FINDINGS: X critical, X high, X medium, X low
RECOMMENDATION: [BLOCK | CAUTION | APPROVE]

TOP ISSUES:
1. <most important issue>
2. <second issue>
3. <third issue>

SUMMARY: <one-paragraph overall assessment>`

export const summaryAgent: AgentDefinition = {
  name: 'summary',
  displayName: 'Summary',
  description: 'Executive summary of all findings with merge recommendation',
  severity: 'info',
  tier: 2,
  needsTools: false,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
}
