import type { Severity, AgentTier } from '../../types/agent-types.ts'

export interface AgentDefinition {
  name: string
  displayName: string
  description: string
  severity: Severity
  tier: AgentTier
  needsTools: boolean
  systemPrompt: string
  buildPrompt: (diff: string, language: string, context?: string) => string
}
