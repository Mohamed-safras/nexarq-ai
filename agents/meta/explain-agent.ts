import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt } from '../agent-template.ts'

const instructions = `Explain what this diff does in plain English for a developer who didn't write it.

Your explanation should:
- Describe what the change does at a high level (one paragraph)
- List the main files changed and what was changed in each
- Explain the likely intent or reason for the change
- Flag anything surprising or non-obvious

Keep the total explanation under 300 words.
Do not reproduce code — describe behavior and intent only.`

export const explainAgent: AgentDefinition = {
  name: 'explain',
  displayName: 'Explain Changes',
  description: 'Plain-English walkthrough of what the diff does and why',
  severity: 'info',
  tier: 2,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
}
