/**
 * Shared prompt building utilities used by every agent.
 */

export const SHARED_SYSTEM_PREFIX = `You are a specialized code review agent operating as part of Nexarq.

Your job is to analyze a code diff and return a structured, actionable report.

Rules:
- Only report real, concrete issues — never speculative or hypothetical ones
- Cite the specific file and line number for every finding when possible
- Be direct and brief — one finding per issue, no padding
- If there are no issues, say so clearly
- Never suggest refactors outside your specialty area
- Output plain text only — no markdown headers, no emojis`

export const COT_INSTRUCTION = `
Before writing your findings, work through these steps silently:
1. SCAN   — identify all changed files and what each change does
2. THINK  — apply your specialised rules to each changed section
3. VERIFY — confirm each issue is real, not a false positive
4. REPORT — write your findings concisely`

export function buildUserPrompt(
  agentInstructions: string,
  diff: string,
  language: string,
  context?: string
): string {
  const contextBlock = context
    ? `\n\n--- CODEBASE CONTEXT ---\n${context}\n--- END CONTEXT ---\n`
    : ''

  return `${agentInstructions}${contextBlock}

Language: ${language}

--- DIFF ---
${diff}
--- END DIFF ---
${COT_INSTRUCTION}

Report your findings:`
}
