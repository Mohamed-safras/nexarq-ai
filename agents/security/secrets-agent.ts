import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt, parseFindings } from '../agent-template.ts'

const instructions = `Focus ONLY on hardcoded secrets and credentials in this diff.

Check for:
- API keys, tokens, passwords committed directly in code
- Private keys or certificates embedded in source files
- Connection strings containing credentials
- Environment variable values hardcoded instead of referenced via process.env
- Patterns matching known secret formats (AWS AKIA*, GitHub ghp_*, etc.)
- Comments containing passwords or access keys

If found, report the file, approximate line, and the type of secret.
Do NOT reproduce the actual secret value in your report.`

export const secretsAgent: AgentDefinition = {
  name: 'secrets',
  displayName: 'Secrets Detection',
  description: 'Hardcoded credentials, API keys, tokens, and private keys',
  severity: 'critical',
  tier: 1,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
  parseFindingsFromOutput: parseFindings,
}
