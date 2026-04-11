import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt } from '../agent-template.ts'

const instructions = `Focus ONLY on code smells and design anti-patterns in this diff.

Check for:
- Long parameter lists (more than 4 — suggest an options object)
- Feature envy (method uses another class's data more than its own)
- Data clumps (same group of variables appearing together repeatedly)
- Primitive obsession (using primitives where a small type/class is clearer)
- Speculative generality (abstractions added for hypothetical future use)
- Divergent change (one class changed for multiple unrelated reasons)
- Shotgun surgery (one change requires edits scattered across many files)`

export const codeSmellsAgent: AgentDefinition = {
  name: 'code_smells',
  displayName: 'Code Smells',
  description: 'Design anti-patterns, feature envy, data clumps, over-engineering',
  severity: 'low',
  tier: 2,
  needsTools: false,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
}
