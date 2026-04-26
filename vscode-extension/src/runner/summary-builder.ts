import type { AgentResult, RunSummary } from '@nexarq/common/interfaces'

export function buildRunSummary(results: AgentResult[]): RunSummary {
  const summary: RunSummary = {
    totalFindings: 0,
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    info: 0,
    agentsRun: results.map((result) => result.agentName),
    tokensUsed: 0,
    estimatedCostUsd: 0,
  }

  for (const result of results) {
    for (const finding of result.findings) {
      const severity = finding.severity ?? 'info'
      summary.totalFindings++
      if (severity in summary) {
        (summary as Record<string, number>)[severity]++
      }
    }
  }

  return summary
}
