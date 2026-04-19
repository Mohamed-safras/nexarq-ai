import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt, parseFindings } from '../agent-template.ts'

const instructions = `Focus ONLY on type safety issues in this diff.

Check for:
- Use of 'any' or untyped variables where specific types can be declared
- Unsafe type assertions (as any, as unknown) without runtime guards
- Missing return type annotations on exported functions
- Missing parameter types on exported functions or methods
- Unchecked narrowing before property access
- Runtime type mismatches TypeScript would catch with stricter settings
- Missing null/undefined checks before property access`

export const typeSafetyAgent: AgentDefinition = {
  name: 'type_safety',
  displayName: 'Type Safety',
  description: "Missing annotations, unsafe 'any' usage, and type assertion abuse",
  severity: 'low',
  tier: 2,
  selectionHints: {
    changeTypes: ['feature', 'refactor'],
    diffContent: ['any', 'as unknown', 'as any', '@ts-ignore', '@ts-nocheck'],
  },
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
  parseFindingsFromOutput: parseFindings,
}
