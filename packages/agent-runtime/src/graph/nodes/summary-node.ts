import { compareSeverity } from '@nexarq/common/utils'
import type { RunSummary } from '@nexarq/common/interfaces'
import type { NexarqGraphState } from '../state.ts'

/**
 * Final node — assembles the results from all review agents into a
 * structured summary and sets `finalOutput` + `isDone`.
 */
export function runSummaryNode(state: NexarqGraphState): Partial<NexarqGraphState> {
  const sortedResults = [...state.agentResults].sort((resultA, resultB) =>
    compareSeverity(resultA.severity, resultB.severity)
  )

  const summary: RunSummary = {
    totalFindings: sortedResults.reduce((total, result) => total + result.findings.length, 0),
    critical: sortedResults.filter((result) => result.severity === 'critical').length,
    high:     sortedResults.filter((result) => result.severity === 'high').length,
    medium:   sortedResults.filter((result) => result.severity === 'medium').length,
    low:      sortedResults.filter((result) => result.severity === 'low').length,
    info:     sortedResults.filter((result) => result.severity === 'info').length,
    agentsRun: sortedResults.map((result) => result.agentName),
    tokensUsed: sortedResults.reduce(
      (total, result) => total + result.tokenUsage.totalTokens, 0
    ),
    estimatedCostUsd: sortedResults.reduce(
      (total, result) => total + (result.tokenUsage.estimatedCostUsd ?? 0), 0
    ),
  }

  const outputLines: string[] = [
    `Nexarq Review — ${summary.agentsRun.length} agents · ` +
    `${summary.critical} critical · ${summary.high} high · ` +
    `${summary.medium} medium · ${summary.low} low`,
    '',
    ...sortedResults
      .filter((result) => result.output.trim().length > 0)
      .map((result) => `[${result.severity.toUpperCase()}] ${result.agentName}\n${result.output}`),
  ]

  return {
    finalOutput: outputLines.join('\n'),
    isDone: true,
  }
}
