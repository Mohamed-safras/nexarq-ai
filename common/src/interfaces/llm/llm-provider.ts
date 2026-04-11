import type { LLMRequest } from './llm-request.js'
import type { LLMResponse } from './llm-response.js'

export interface ILLMProvider {
  name: string
  defaultModel: string
  complete(request: LLMRequest): Promise<LLMResponse>
  stream(request: LLMRequest): AsyncGenerator<string>
  healthCheck(): Promise<boolean>
  listModels(): Promise<string[]>
}
