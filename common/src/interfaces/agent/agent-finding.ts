import type { Severity } from '../../types/agent-types.ts'

export interface AgentFinding {
  line?: number
  file?: string
  message: string
  suggestion?: string
  severity?: Severity
  ruleId?: string
}
