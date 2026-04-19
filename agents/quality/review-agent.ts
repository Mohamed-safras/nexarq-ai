import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt, parseFindings } from '../agent-template.ts'

const instructions = `Perform a general code quality review of this diff.

Check for:
- Unclear or misleading variable and function names
- Functions doing too many things (single responsibility violation)
- Duplicated logic that should be extracted into a shared function
- Missing or incorrect edge case handling
- Overly complex conditionals that could be simplified
- Dead code (unreachable branches, unused variables)
- Magic numbers or strings without named constants
- Inconsistent patterns with the surrounding codebase`

export const reviewAgent: AgentDefinition = {
  name: 'review',
  displayName: 'Code Review',
  description: 'General code quality, naming, complexity, and best practices',
  severity: 'medium',
  tier: 2,
  selectionHints: {
    changeTypes: ['feature', 'general'],
  },
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
  parseFindingsFromOutput: parseFindings,
}
