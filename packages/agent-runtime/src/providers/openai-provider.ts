import { ChatOpenAI } from '@langchain/openai'
import type { IProvider, ProviderConfig } from './base-provider.ts'
import { PROVIDER_DEFAULT_MODELS, PROVIDER_MODELS } from '@nexarq/common/constants'

export class OpenAIProvider implements IProvider {
  readonly providerName = 'openai' as const
  readonly defaultModel = PROVIDER_DEFAULT_MODELS.openai

  buildModel(config?: ProviderConfig): ChatOpenAI {
    return new ChatOpenAI({
      model: config?.model ?? this.defaultModel,
      temperature: config?.temperature ?? 0.2,
      maxTokens: config?.maxTokens ?? 4096,
      apiKey: process.env['NEXARQ_OPENAI_API_KEY'],
    })
  }

  async listModels(): Promise<string[]> {
    return PROVIDER_MODELS.openai
  }

  async healthCheck(): Promise<boolean> {
    try {
      const chatModel = this.buildModel({ maxTokens: 1 })
      await chatModel.invoke('ping')
      return true
    } catch {
      return false
    }
  }
}
