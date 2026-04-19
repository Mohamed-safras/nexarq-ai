import type { AgentDefinition } from '@nexarq/common/interfaces'
import { parseFindings } from '../agent-template.ts'

/**
 * System prompt for the deep analysis agent.
 * Unlike SHARED_SYSTEM_PREFIX, this explicitly tells Claude it has extended
 * thinking time and should use it for multi-hop reasoning before reporting.
 */
const DEEP_ANALYSIS_SYSTEM = `You are a senior application security engineer conducting a deep-dive code review.

You have extended thinking time — use it to trace full attack paths, not just spot surface patterns.

Rules:
- Reason through the full exploit chain before reporting a finding (how would an attacker actually use this?)
- Use web_search to look up CVEs or advisories when you identify a known vulnerability class
- Use read_file and search_code to trace how user-controlled data flows through the codebase
- Format each finding on its own line starting with FINDING:
  FINDING: path/to/file.ts:42 — description of the issue
  SUGGESTION: how to fix it (optional, one line)
  CVE: CVE-YYYY-NNNN (include only when you confirmed one via web_search)
- Only report issues that are reachable and exploitable — no theoretical findings
- If there are no exploitable issues, write: NO FINDINGS`

const instructions = `Perform deep security analysis of this diff.

Focus areas (in priority order):
1. Authentication and authorization bypass paths
2. Injection vulnerabilities (SQL, command, LDAP, XPath, template)
3. Cryptographic misuse (weak algorithms, hardcoded keys, IV reuse, timing attacks)
4. Deserialization of untrusted data
5. SSRF and open redirect via user-controlled URLs
6. Race conditions in security-sensitive operations
7. Insecure direct object references and mass assignment

For each suspected issue:
- Trace the full data flow from entry point to sink using read_file/search_code
- Use web_search to confirm whether known CVEs apply (e.g. "lodash prototype pollution CVE")
- Only report after confirming the vulnerability is reachable`

export const deepAnalysisAgent: AgentDefinition = {
  name: 'deep_analysis',
  displayName: 'Deep Security Analysis',
  description: 'Extended-thinking agent that traces full attack paths and looks up CVEs via web search',
  severity: 'critical',
  tier: 2,
  usesExtendedThinking: true,
  selectionHints: {
    diffContent: [
      'password', 'token', 'secret', 'auth', 'login', 'session', 'cookie',
      'jwt', 'oauth', 'crypto', 'encrypt', 'decrypt', 'hash', 'sign',
      'sql', 'query', 'exec', 'eval', 'deserializ', 'unpickle',
      'fetch(', 'axios', 'request(', 'http.get', 'url', 'redirect',
      'permission', 'role', 'admin', 'sudo', 'privilege',
    ],
    filePaths: ['auth', 'login', 'session', 'crypto', 'password', 'token', 'middleware', 'guard'],
  },
  systemPrompt: DEEP_ANALYSIS_SYSTEM,
  buildPrompt: (diff, language, context) => {
    const contextBlock = context
      ? `\n\n--- PROJECT KNOWLEDGE ---\n${context}\n--- END PROJECT KNOWLEDGE ---\n`
      : ''

    return `${instructions}${contextBlock}

Language: ${language}

--- DIFF ---
${diff}
--- END DIFF ---

Begin your analysis. Use tools to trace data flows and confirm findings before reporting.`
  },
  parseFindingsFromOutput: parseFindings,
}
