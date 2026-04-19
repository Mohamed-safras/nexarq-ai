import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt, parseFindings } from '../agent-template.ts'

const instructions = `Focus ONLY on architectural and design concerns in this diff.

Check for:
- Violations of separation of concerns (business logic in UI or data layer)
- Tight coupling between modules that should be independent
- Circular dependencies introduced by new imports
- Dependency inversion principle violations
- God objects or classes accumulating too many responsibilities
- Internal implementation details leaking across module boundaries
- Inappropriate use of global or shared mutable state`

export const architectureAgent: AgentDefinition = {
  name: 'architecture',
  displayName: 'Architecture',
  description: 'SOLID principles, coupling, layering, and module boundaries',
  severity: 'medium',
  tier: 2,
  selectionHints: {
    changeTypes: ['refactor', 'feature'],
    diffContent: ['import ', 'require(', 'from \'', 'from "'],
  },
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
  parseFindingsFromOutput: parseFindings,
}
