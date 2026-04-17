import type { AgentResult } from '../agent/agent-result.ts'
import type { RunSummary } from './run-summary.ts'

export interface RunResponse {
  runId: string
  results: AgentResult[]
  durationMs: number
  summary: RunSummary
}
