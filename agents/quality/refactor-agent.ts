import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt } from '../agent-template.ts'

const instructions = `Focus ONLY on refactoring opportunities in this diff.

Identify code that could be simplified, deduplicated, or restructured:
- Duplicated logic that can be extracted into a shared function
- Nested conditionals that could be flattened using early returns
- Complex chains that could benefit from intermediate named variables
- Loops that could be replaced with standard array methods (map, filter, reduce)
- Large functions that should be broken into smaller named steps
- Inline logic that would be clearer as a named helper

Suggest concrete, specific improvements — not vague "clean this up" advice.`

export const refactorAgent: AgentDefinition = {
  name: 'refactor',
  displayName: 'Refactoring',
  description: 'DRY violations, nested conditionals, and complexity reduction opportunities',
  severity: 'low',
  tier: 2,
  needsTools: false,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
}
