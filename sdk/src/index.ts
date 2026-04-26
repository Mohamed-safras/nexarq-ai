export { NexarqClient } from './client.ts'
export type { NexarqClientOptions, ReviewOptions, CodeOptions } from './client.ts'

// Re-export common types so SDK consumers don't need @nexarq/common
export type {
  RunEvent,
  Severity,
  AgentMode,
  ProviderName,
} from '@nexarq/common/types'

export type {
  AgentResult,
  AgentFinding,
  RunSummary,
  RunConfig,
  RunResponse,
} from '@nexarq/common/interfaces'