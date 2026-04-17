import type { LLMRequest } from './llm-request.ts'
import type { LLMResponse } from './llm-response.ts'

export interface ILLMProvider {
  name: string
  defaultModel: string
  complete(request: LLMRequest): Promise<LLMResponse>
  stream(request: LLMRequest): AsyncGenerator<string>
  healthCheck(): Promise<boolean>
  listModels(): Promise<string[]>
}
