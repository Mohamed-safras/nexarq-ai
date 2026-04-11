import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt } from '../agent-template.ts'

const instructions = `Focus ONLY on memory safety and resource leak issues in this diff.

Check for:
- Buffer overflows or out-of-bounds array access
- Use-after-free patterns (in systems languages)
- Memory allocated but never freed (in languages without GC)
- File handles, connections, or streams opened but not closed in error paths
- Large allocations without size bounds checks
- Unbounded data accumulation in long-running processes
- Circular references preventing garbage collection`

export const memorySafetyAgent: AgentDefinition = {
  name: 'memory_safety',
  displayName: 'Memory Safety',
  description: 'Buffer overflows, use-after-free, and resource leak patterns',
  severity: 'high',
  tier: 2,
  needsTools: false,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
}
