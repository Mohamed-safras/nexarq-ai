import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt } from '../agent-template.ts'

const instructions = `Based on this diff, recommend the most valuable next steps for the developer.

Produce a prioritised action list:
- Immediate (must fix before merge): blocking issues
- Soon (fix in the next sprint): important improvements
- Consider (optional improvements): nice-to-haves

Each item should be a single, concrete, actionable task.
Maximum 8 items total. No vague suggestions.

Format:
IMMEDIATE:
- <task>

SOON:
- <task>

CONSIDER:
- <task>`

export const nextStepsAgent: AgentDefinition = {
  name: 'next_steps',
  displayName: 'Next Steps',
  description: 'Prioritised action list of what to fix and improve',
  severity: 'info',
  tier: 2,
  needsTools: false,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
}
