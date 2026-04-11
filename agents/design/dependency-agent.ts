import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt } from '../agent-template.ts'

const instructions = `Focus ONLY on dependency and package management concerns in this diff.

Check for:
- New packages added with known vulnerabilities (check the package name and version range)
- Overly broad version ranges (e.g. "*" or ">= 1.0.0") that may pull in breaking changes
- Packages added that duplicate existing dependencies
- Dev dependencies incorrectly placed in production dependencies
- Packages removed that may still be referenced in code
- Lock file changes not matching manifest changes
- New packages from unverified or low-trust publishers`

export const dependencyAgent: AgentDefinition = {
  name: 'dependency',
  displayName: 'Dependencies',
  description: 'Vulnerable packages, broad version ranges, and dependency hygiene',
  severity: 'high',
  tier: 2,
  needsTools: false,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
}
