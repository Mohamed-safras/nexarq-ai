import type { AgentResult } from '../agent/agent-result.js'
import type { RunSummary } from './run-summary.js'

export interface RunResponse {
  runId: string
  results: AgentResult[]
  durationMs: number
  summary: RunSummary
}
