export interface RunSummary {
  totalFindings: number
  critical: number
  high: number
  medium: number
  low: number
  info: number
  agentsRun: string[]
  tokensUsed: number
  estimatedCostUsd: number
}
