import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt, parseFindings } from '../agent-template.ts'

const instructions = `Focus ONLY on resource management issues in this diff.

Check for:
- File descriptors or streams opened without guaranteed close (no try/finally or using/defer)
- Database connections not returned to the pool
- HTTP clients or sockets not closed after use
- Timers or intervals created but never cleared
- Event listeners added but never removed
- Large files read entirely into memory instead of being streamed
- Missing timeouts on external calls (HTTP requests, DB queries)`

export const resourceUsageAgent: AgentDefinition = {
  name: 'resource_usage',
  displayName: 'Resource Usage',
  description: 'File handles, connections, timers, and listeners not properly released',
  severity: 'medium',
  tier: 2,
  selectionHints: {
    changeTypes: ['performance', 'feature'],
    diffContent: ['setInterval', 'setTimeout', 'addEventListener', 'createReadStream', 'createWriteStream', 'fs.open', 'pool'],
  },
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
  parseFindingsFromOutput: parseFindings,
}
