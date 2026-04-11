import type { ProviderName } from '../../types/agent-types.js'
import type { TokenUsage } from '../agent/token-usage.js'

export interface LLMResponse {
  text: string
  provider: ProviderName
  model: string
  usage: TokenUsage
  latencyMs: number
  cached: boolean
}
