import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt, parseFindings } from '../agent-template.ts'

const instructions = `Focus ONLY on maintainability concerns in this diff.

Check for:
- Functions or methods exceeding ~40 lines (too long to understand at a glance)
- High cyclomatic complexity (deeply nested if/else or switch chains)
- Deeply nested code blocks (more than 3–4 levels of indentation)
- Hard-coded constants that should be named and centralized
- Tightly coupled code that makes future changes difficult
- Missing abstraction where the same pattern repeats 3+ times
- Code that is hard to test due to hidden dependencies or global state`

export const maintainabilityAgent: AgentDefinition = {
  name: 'maintainability',
  displayName: 'Maintainability',
  description: 'Function length, cyclomatic complexity, and coupling issues',
  severity: 'medium',
  tier: 2,
  selectionHints: {
    changeTypes: ['refactor', 'feature'],
  },
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
  parseFindingsFromOutput: parseFindings,
}
