import type { AgentMode, ProviderName } from '../../types/agent-types.ts'

export interface RunConfig {
  agents?: string[]
  mode?: AgentMode
  provider?: ProviderName
  model?: string
  maxAgents?: number
  cloudConsent?: boolean
  redactSecrets?: boolean
  toolCallBudget?: number
  streamResults?: boolean
}
