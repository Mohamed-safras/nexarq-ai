import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt, parseFindings } from '../agent-template.ts'

const instructions = `Focus ONLY on concurrency and thread-safety issues in this diff.

Check for:
- Race conditions on shared mutable state accessed from multiple async contexts
- Missing mutex or lock around critical sections
- Deadlock potential (nested locks, inconsistent lock ordering)
- Missing await on async calls (fire-and-forget without intent)
- Non-atomic check-then-act patterns
- Missing cancellation signal handling in long-running operations
- Promise.all failures not handled atomically`

export const concurrencyAgent: AgentDefinition = {
  name: 'concurrency',
  displayName: 'Concurrency',
  description: 'Race conditions, deadlocks, thread safety, and async correctness',
  severity: 'high',
  tier: 2,
  selectionHints: {
    diffContent: ['async ', 'await ', 'thread', 'mutex', 'semaphore', 'Promise.all', 'Promise.race', 'concurrent'],
  },
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
  parseFindingsFromOutput: parseFindings,
}
