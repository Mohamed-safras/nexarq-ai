import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt, parseFindings } from '../agent-template.ts'

const instructions = `Focus ONLY on error handling patterns in this diff.

Check for:
- Empty catch blocks that silently swallow errors
- Catching overly broad exception types
- Missing finally blocks where resource cleanup is required
- Rethrowing errors without preserving the original stack trace
- Missing propagation to callers (returning null instead of throwing)
- User-facing messages that expose internal stack traces
- Missing retry logic for transient failures (network, I/O)
- Unhandled promise rejections`

export const errorHandlingAgent: AgentDefinition = {
  name: 'error_handling',
  displayName: 'Error Handling',
  description: 'Silent failures, swallowed exceptions, missing propagation',
  severity: 'medium',
  tier: 2,
  selectionHints: {
    changeTypes: ['bugfix', 'feature'],
    diffContent: ['catch', 'try {', '.catch(', 'throw ', 'reject('],
  },
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
  parseFindingsFromOutput: parseFindings,
}
