import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt, parseFindings } from '../agent-template.ts'

const instructions = `Focus ONLY on API design quality in this diff.

Check for:
- Inconsistent HTTP method usage (e.g. GET with side effects)
- Missing or incorrect HTTP status codes
- Non-RESTful URL patterns (verbs in paths, inconsistent pluralisation)
- Missing pagination or filtering on list endpoints
- Breaking changes to existing public API contracts
- Inconsistent error response shapes
- Missing API versioning strategy
- GraphQL: N+1 resolver patterns, missing depth limits, over-fetching`

export const apiDesignAgent: AgentDefinition = {
  name: 'api_design',
  displayName: 'API Design',
  description: 'REST/GraphQL conventions, status codes, versioning, and response contracts',
  severity: 'medium',
  tier: 2,
  selectionHints: {
    diffContent: ['route', 'endpoint', 'router.', 'app.get', 'app.post', 'app.put', 'app.delete', 'graphql', 'resolver'],
  },
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
  parseFindingsFromOutput: parseFindings,
}
