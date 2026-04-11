import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt } from '../agent-template.ts'

const instructions = `Focus ONLY on documentation and comment quality in this diff.

Check for:
- Public functions, classes, or methods missing JSDoc/docstring comments
- Exported types or interfaces missing descriptions
- Outdated comments that no longer reflect the current code
- Comments that just restate what the code does (not explaining why)
- Complex algorithms or non-obvious logic missing explanation comments
- API endpoints missing parameter and response documentation
- README references to removed or renamed exports`

export const docstringAgent: AgentDefinition = {
  name: 'docstring',
  displayName: 'Documentation',
  description: 'Missing JSDoc, outdated comments, and undocumented public APIs',
  severity: 'low',
  tier: 2,
  needsTools: false,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
}
