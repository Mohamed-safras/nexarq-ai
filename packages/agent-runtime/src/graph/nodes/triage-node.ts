import type { AgentResult } from '@nexarq/common/interfaces'
import type { NexarqGraphState } from '../state.ts'
import { runReactAgent } from './workflow/node-utils.ts'
import { getReadTools } from '../../tools/read-tools.ts'
import { getTerminalTools } from '../../tools/terminal-tools.ts'

const TRIAGE_SYSTEM = `You are the Nexarq triage coordinator. You run after the parallel review agents complete.

Your job:
1. CROSS-CHECK — verify high-severity findings using read_file and search_code (confirm the vulnerable code path is actually reachable)
2. VALIDATE — run run_validation (tsc --noEmit, bun test) when findings suggest type errors or broken logic
3. GAP-FILL — identify cross-cutting issues the siloed agents couldn't see (e.g. security agent found auth bypass, does the bug agent know the affected callers?)
4. WEB-CONFIRM — for findings that mention known vulnerability classes, use web_search to confirm CVEs

Rules:
- Only report NEW findings not already covered by the parallel agents
- Each new finding: TRIAGE-FINDING: path/to/file.ts:line — description
- If validation passes cleanly: VALIDATION: tsc — PASS
- If validation reveals new issues: TRIAGE-FINDING: ... (from compiler/test output)
- If nothing new found: write TRIAGE: no additional findings
- Be concise — max 300 words total`

function formatFindingsContext(results: AgentResult[]): string {
  const lines: string[] = []
  for (const r of results) {
    if (!r.output.trim() || r.output.includes('NO FINDINGS')) continue
    lines.push(`=== ${r.agentName.toUpperCase()} [${r.severity}] ===`)
    // Include only FINDING: lines to keep context tight
    const findingLines = r.output
      .split('\n')
      .filter((l) => l.startsWith('FINDING:') || l.startsWith('SUGGESTION:'))
      .slice(0, 10)
    if (findingLines.length > 0) {
      lines.push(...findingLines)
    } else {
      lines.push(r.output.slice(0, 400))
    }
    lines.push('')
  }
  return lines.join('\n')
}

/**
 * Triage node — runs between the parallel fan-out and the summary node.
 *
 * Unlike the siloed review agents (each sees only its domain), the triage node:
 * - Sees ALL findings from all agents simultaneously
 * - Can run terminal validation to confirm or deny type/logic findings
 * - Can do targeted codebase searches to trace cross-agent findings
 * - Can look up CVEs via web_search
 *
 * In 'fast' mode the triage node is skipped (direct to summary).
 * In 'smart' and 'deep' modes it runs after the parallel fan-out.
 */
export async function runTriageNode(state: NexarqGraphState): Promise<Partial<NexarqGraphState>> {
  const mode = state.runConfig.mode ?? 'smart'

  // Skip in fast mode — speed is the priority
  if (mode === 'fast') return { triageOutput: '' }

  // Skip if no results came back
  if (state.agentResults.length === 0) return { triageOutput: '' }

  const criticalOrHigh = state.agentResults.filter(
    (r) => r.severity === 'critical' || r.severity === 'high'
  )

  // In 'smart' mode skip if nothing critical/high — not worth the extra latency
  if (mode === 'smart' && criticalOrHigh.length === 0) return { triageOutput: '' }

  state.onEvent?.({ type: 'agent:start', agentName: 'triage' })
  const startTime = Date.now()

  const findingsContext = formatFindingsContext(state.agentResults)
  const workingDirectory = state.workingDirectory ?? process.cwd()
  const tools = [...getReadTools(workingDirectory), ...getTerminalTools(workingDirectory)]

  const userPrompt = `Here are all findings from the parallel review agents:

${findingsContext}

Diff language: ${state.diffResult?.primaryLanguage ?? 'unknown'}
Working directory: ${workingDirectory}

Your task:
1. Cross-check the CRITICAL and HIGH findings above — use read_file/search_code to confirm they are real and reachable
2. Run run_validation ("tsc --noEmit" or project-appropriate command) if there are type-safety or bug findings
3. Report any NEW findings you discover that the agents missed
4. Report validation results (PASS / FAIL with details)

Be concise. Focus on what adds new information.`

  try {
    const output = await runReactAgent(
      state.runConfig,
      TRIAGE_SYSTEM,
      userPrompt,
      tools,
      { temperature: 0.1, maxTokens: 2048 }
    )

    state.onEvent?.({
      type: 'agent:complete',
      result: {
        agentName: 'triage',
        severity: 'info',
        output,
        findings: [],
        warnings: [],
        tokenUsage: { promptTokens: 0, completionTokens: 0, totalTokens: 0 },
        latencyMs: Date.now() - startTime,
        cached: false,
      },
    })

    return { triageOutput: output }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    state.onEvent?.({ type: 'agent:error', agentName: 'triage', error: msg })
    return { triageOutput: '' }
  }
}
