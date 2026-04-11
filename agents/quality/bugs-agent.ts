import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt } from '../agent-template.ts'

const instructions = `Focus ONLY on logic errors, bugs, and incorrect behavior in this diff.

Check for:
- Null/undefined dereference without guards
- Off-by-one errors in loops or array access
- Incorrect conditional logic (wrong operators, missing branches)
- Unhandled promise rejections or missing awaits
- Silent failures (errors swallowed without logging or re-throwing)
- Incorrect equality checks (== vs ===, reference vs value)
- Mutation of shared state or function arguments unexpectedly
- Race conditions in async code`

export const bugsAgent: AgentDefinition = {
  name: 'bugs',
  displayName: 'Bug Detection',
  description: 'Logic errors, null dereferences, async issues, and incorrect behavior',
  severity: 'high',
  tier: 1,
  needsTools: true,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
}
