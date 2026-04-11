// MiniMax M1 — OpenAI-compatible API used by Codebuff's free tier
// ~$0.10/1M input tokens — 30x cheaper than GPT-4o, competitive quality on coding tasks
// API docs: https://platform.minimaxi.com/document/Chatcompletion%20v2
import { ChatOpenAI } from '@langchain/openai'
import type { IProvider, ProviderConfig } from './base-provider.ts'
import { PROVIDER_DEFAULT_MODELS, PROVIDER_MODELS, MINIMAX_DEFAULT_URL } from '@nexarq/common/constants'

export class MinimaxProvider implements IProvider {
  readonly providerName = 'minimax' as const
  readonly defaultModel  = PROVIDER_DEFAULT_MODELS.minimax

  buildModel(config?: ProviderConfig): ChatOpenAI {
    // MiniMax exposes an OpenAI-compatible chat endpoint — reuse ChatOpenAI
    return new ChatOpenAI({
      model:       config?.model ?? this.defaultModel,
      temperature: config?.temperature ?? 0.2,
      maxTokens:   config?.maxTokens ?? 4096,
      apiKey:      process.env['NEXARQ_MINIMAX_API_KEY'] ?? 'no-key',
      configuration: {
        baseURL: process.env['NEXARQ_MINIMAX_URL'] ?? MINIMAX_DEFAULT_URL,
      },
    })
  }

  async listModels(): Promise<string[]> {
    return PROVIDER_MODELS.minimax
  }

  async healthCheck(): Promise<boolean> {
    const apiKey = process.env['NEXARQ_MINIMAX_API_KEY']
    if (!apiKey) return false
    try {
      const chatModel = this.buildModel({ maxTokens: 1 })
      await chatModel.invoke('ping')
      return true
    } catch {
      return false
    }
  }
}
