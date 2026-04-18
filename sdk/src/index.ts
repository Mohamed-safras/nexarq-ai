export { NexarqClient } from './client.ts'
export type { NexarqClientOptions, ReviewOptions, CodeOptions } from './client.ts'

// Re-export common types so SDK consumers don't need @nexarq/common
export type {
  AgentResult,
  AgentFinding,
  RunSummary,
  RunEvent,
  Severity,
  AgentMode,
  ProviderName,
} from '@nexarq/common/types'
export type { RunConfig, RunResponse } from '@nexarq/common/interfaces'
