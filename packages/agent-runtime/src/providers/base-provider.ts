import type { ProviderName } from '@nexarq/common/types'

export interface ProviderConfig {
  model?: string
  temperature?: number
  maxTokens?: number
}

/**
 * Every provider wraps a LangChain BaseChatModel.
 * `buildModel()` returns the concrete chat model instance which the
 * LangGraph graph nodes use directly — so model switching happens in
 * one place without touching any graph logic.
 */
export interface IProvider {
  readonly providerName: ProviderName
  readonly defaultModel: string
  // Returns a LangChain BaseChatModel — typed as `unknown` here to avoid
  // requiring @langchain/core at compile time before install. Each concrete
  // provider is fully typed internally.
  buildModel(config?: ProviderConfig): unknown
  listModels(): Promise<string[]>
  healthCheck(): Promise<boolean>
}
