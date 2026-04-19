import type { AgentDefinition } from '@nexarq/common/interfaces'
import { SHARED_SYSTEM_PREFIX, buildUserPrompt, parseFindings } from '../agent-template.ts'

const instructions = `Focus ONLY on security vulnerabilities in this diff.

Check for:
- OWASP Top 10 (injection, broken auth, XSS, IDOR, SSRF, etc.)
- Hardcoded credentials or secrets in code
- Missing input validation or sanitization
- Insecure deserialization
- Broken access control (missing auth checks, privilege escalation)
- Cryptographic weaknesses (weak algorithms, improper key handling)
- SQL, command, or path injection vulnerabilities
- Unprotected sensitive data exposure`

export const securityAgent: AgentDefinition = {
  name: 'security',
  displayName: 'Security',
  description: 'OWASP Top 10, injection flaws, auth issues, and sensitive data exposure',
  severity: 'critical',
  tier: 1,
  systemPrompt: SHARED_SYSTEM_PREFIX,
  buildPrompt: (diff, language, context) => buildUserPrompt(instructions, diff, language, context),
  parseFindingsFromOutput: parseFindings,
}
