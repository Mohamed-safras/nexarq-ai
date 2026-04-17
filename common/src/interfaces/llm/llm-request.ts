import type { ProviderName } from '../../types/agent-types.ts'

export interface LLMRequest {
  systemPrompt: string
  userPrompt: string
  model: string
  provider: ProviderName
  maxTokens?: number
  temperature?: number
  stream?: boolean
}
