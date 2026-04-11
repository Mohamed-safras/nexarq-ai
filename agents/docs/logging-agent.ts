import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt } from '../agent-template.ts'

const instructions = `Focus ONLY on logging quality and privacy issues in this diff.

Check for:
- PII or sensitive data logged (passwords, tokens, email addresses, phone numbers)
- Logging at incorrect levels (using console.log in production code, DEBUG in hot paths)
- Missing error logging in catch blocks
- Logs that include raw request/response bodies containing user data
- Excessive logging in tight loops (performance impact)
- Log messages that are too vague to be actionable for debugging
- Missing structured logging fields (no correlation ID, no request context)`

export const loggingAgent: AgentDefinition = {
  name: 'logging',
  displayName: 'Logging',
  description: 'PII in logs, incorrect log levels, missing error logs',
  severity: 'medium',
  tier: 2,
  needsTools: false,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
}
