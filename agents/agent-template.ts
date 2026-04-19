/**
 * Shared system prompt prefix injected into every review agent.
 * Keep this stable — it's the cache-warm prefix for all agents.
 */
export const SHARED_SYSTEM_PREFIX = `You are a specialized code review agent operating as part of Nexarq.

Your job is to analyze a code diff and return a structured, actionable report.

Rules:
- Only report real, concrete issues — never speculative or hypothetical ones
- Cite the specific file and line number for every finding
- Format each finding on its own line starting with FINDING:
  FINDING: path/to/file.ts:42 — description of the issue
  SUGGESTION: how to fix it (optional, one line)
- If there are no issues in your area, write: NO FINDINGS
- Be direct and brief — one FINDING line per issue, no padding
- Never suggest refactors outside your specialty area`

/**
 * Chain-of-thought scaffold appended to every user prompt.
 * Placed after the diff so it breaks the cache intentionally (diff varies per run).
 */
export const COT_INSTRUCTION = `
Before writing your findings, work through these steps silently:
1. SCAN   — identify all changed files and what each change does
2. THINK  — apply your specialised rules to each changed section
3. VERIFY — confirm each issue is real, not a false positive
4. REPORT — write your findings using the FINDING: format`

export function buildUserPrompt(
  agentInstructions: string,
  diff: string,
  language: string,
  context?: string
): string {
  const contextBlock = context
    ? `\n\n--- PROJECT KNOWLEDGE ---\n${context}\n--- END PROJECT KNOWLEDGE ---\n`
    : ''

  return `${agentInstructions}${contextBlock}

Language: ${language}

--- DIFF ---
${diff}
--- END DIFF ---
${COT_INSTRUCTION}

Report your findings:`
}

/**
 * Parses structured findings from agent output.
 *
 * Matches lines in the format:
 *   FINDING: path/to/file.ts:42 — description
 *   SUGGESTION: optional fix
 *
 * Shared by all agents via `parseFindingsFromOutput: parseFindings`.
 */
export function parseFindings(output: string): { file?: string; line?: number; message: string; suggestion?: string; ruleId?: string }[] {
  const findings: { file?: string; line?: number; message: string; suggestion?: string; ruleId?: string }[] = []
  const lines = output.split('\n')

  let i = 0
  while (i < lines.length) {
    const line = lines[i] ?? ''
    const findingMatch = line.match(/^FINDING:\s+(.+)/)
    if (!findingMatch) { i++; continue }

    const body = findingMatch[1] ?? ''

    // Parse optional file:line prefix: "src/auth.ts:42 — message"
    const fileLineMatch = body.match(/^([^\s:]+):(\d+)\s*[—–-]+\s*(.+)/)
    if (fileLineMatch) {
      const suggestion = extractSuggestion(lines, i + 1)
      const finding: { file?: string; line?: number; message: string; suggestion?: string } = {
        message: (fileLineMatch[3] ?? '').trim(),
        line: parseInt(fileLineMatch[2] ?? '0', 10),
      }
      if (fileLineMatch[1]) finding.file = fileLineMatch[1]
      if (suggestion) finding.suggestion = suggestion
      findings.push(finding)
      if (suggestion) i++ // consumed SUGGESTION line
    } else {
      // No file:line — just a message
      findings.push({ message: body.trim() })
    }

    i++
  }

  return findings
}

function extractSuggestion(lines: string[], nextIndex: number): string | undefined {
  const next = lines[nextIndex] ?? ''
  const match = next.match(/^SUGGESTION:\s+(.+)/)
  return match ? (match[1] ?? '').trim() : undefined
}
