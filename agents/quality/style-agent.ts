import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt, parseFindings } from '../agent-template.ts'

const instructions = `Focus ONLY on code style and formatting consistency in this diff.

Check for:
- Naming convention inconsistencies (camelCase vs snake_case mixed in same file)
- Inconsistent indentation or spacing
- Line length violations beyond the project's apparent limit
- Inconsistent import ordering style
- Trailing whitespace or mixed line endings
- Unused imports not removed
- Inconsistent quote style (single vs double quotes mixed)

Only flag issues that are clearly inconsistent with the surrounding code.`

export const styleAgent: AgentDefinition = {
  name: 'style',
  displayName: 'Style',
  description: 'Naming conventions, formatting consistency, and import ordering',
  severity: 'low',
  tier: 2,
  selectionHints: {
    changeTypes: ['refactor', 'feature', 'general'],
  },
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
  parseFindingsFromOutput: parseFindings,
}
