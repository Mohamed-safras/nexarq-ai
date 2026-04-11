import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt } from '../agent-template.ts'

const instructions = `You will be given findings from other review agents. For each finding, generate a concrete code fix.

For every finding:
1. Quote the problematic code (from the diff)
2. Write the corrected replacement code
3. One sentence explaining what changed and why

Format each fix as:
FINDING: <agent name> — <brief issue description>
BEFORE:
<original code>
AFTER:
<fixed code>
REASON: <one sentence>

Only generate fixes for CRITICAL and HIGH severity findings.
Skip INFO and LOW findings.`

export const aiFixesAgent: AgentDefinition = {
  name: 'ai_fixes',
  displayName: 'AI Fixes',
  description: 'Generates concrete code fix suggestions for CRITICAL and HIGH findings',
  severity: 'info',
  tier: 2,
  needsTools: false,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
}
