import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt } from '../agent-template.ts'

const instructions = `Focus ONLY on project-specific coding standards in this diff.

Review the diff against any coding standards found in the repository context
(CONTRIBUTING.md, .eslintrc, coding_standards.md, AGENTS.md, etc.).

Check for:
- Violations of the project's stated naming conventions
- Patterns that conflict with the project's established architecture
- Files placed in the wrong directory per the project structure
- Forbidden patterns or imports explicitly called out in project docs
- PR or commit message format violations`

export const standardsAgent: AgentDefinition = {
  name: 'standards',
  displayName: 'Standards',
  description: 'Project-specific coding standards and convention adherence',
  severity: 'low',
  tier: 2,
  needsTools: true,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
}
