import type { Severity } from '../../types/agent-types.ts'
import type { AgentFinding } from './agent-finding.ts'
import type { TokenUsage } from './token-usage.ts'

export interface AgentResult {
  agentName: string
  severity: Severity
  output: string
  findings: AgentFinding[]
  warnings: string[]
  tokenUsage: TokenUsage
  latencyMs: number
  error?: string
  cached: boolean
}
