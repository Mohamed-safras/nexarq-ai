import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt, parseFindings } from '../agent-template.ts'

const instructions = `Focus ONLY on performance issues introduced by this diff.

Check for:
- N+1 query patterns (database calls inside loops)
- Unnecessary repeated computation in hot paths
- Missing memoization or caching for expensive operations
- Synchronous blocking calls in async contexts
- Unbounded loops or recursion without limits
- Inefficient data structures (O(n) array lookup where Set/Map would be O(1))
- Large object allocations inside tight loops
- Missing pagination on queries that could return unbounded rows`

export const performanceAgent: AgentDefinition = {
  name: 'performance',
  displayName: 'Performance',
  description: 'N+1 queries, unnecessary computation, blocking calls, inefficient structures',
  severity: 'high',
  tier: 2,
  selectionHints: {
    changeTypes: ['performance', 'database'],
    diffContent: ['for (', 'while (', 'forEach', '.map(', 'SELECT', 'findAll', 'findMany'],
  },
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
  parseFindingsFromOutput: parseFindings,
}
