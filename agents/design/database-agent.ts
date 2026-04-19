import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt, parseFindings } from '../agent-template.ts'

const instructions = `Focus ONLY on database and data-layer concerns in this diff.

Check for:
- SQL injection via raw string interpolation in queries
- Missing transactions for operations that must be atomic
- Missing indexes on columns used in WHERE, JOIN, or ORDER BY
- N+1 query patterns in ORM usage
- Unsafe migrations (dropping columns, removing NOT NULL without defaults)
- Storing sensitive data without encryption at rest
- Unbounded SELECT queries with no LIMIT
- ORM misuse that bypasses validation or constraints`

export const databaseAgent: AgentDefinition = {
  name: 'database',
  displayName: 'Database',
  description: 'SQL injection, schema safety, missing indexes, and migration issues',
  severity: 'high',
  tier: 2,
  selectionHints: {
    changeTypes: ['database'],
    filePaths: ['migration', 'schema', 'query', 'model', 'repository', 'prisma', 'drizzle'],
  },
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
  parseFindingsFromOutput: parseFindings,
}
