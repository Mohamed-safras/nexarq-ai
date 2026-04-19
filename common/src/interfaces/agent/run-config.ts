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
  /**
   * When true, the shell tool runs without an allowlist — any command except
   * permanently destructive ops (rm -rf /, disk writes) is permitted.
   * Enables: package installs, migrations, deploys, dev server start.
   * Must be explicitly set — never enabled by default.
   */
  unsafeShell?: boolean
}
