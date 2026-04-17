import type { ProviderName } from '../../types/agent-types.ts'
import type { TokenUsage } from '../agent/token-usage.ts'

export interface LLMResponse {
  text: string
  provider: ProviderName
  model: string
  usage: TokenUsage
  latencyMs: number
  cached: boolean
}
