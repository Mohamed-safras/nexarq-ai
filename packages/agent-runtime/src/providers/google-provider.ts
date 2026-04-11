import { ChatGoogleGenerativeAI } from '@langchain/google-genai'
import type { IProvider, ProviderConfig } from './base-provider.ts'
import { PROVIDER_DEFAULT_MODELS, PROVIDER_MODELS } from '@nexarq/common/constants'

export class GoogleProvider implements IProvider {
  readonly providerName = 'google' as const
  readonly defaultModel = PROVIDER_DEFAULT_MODELS.google

  buildModel(config?: ProviderConfig): ChatGoogleGenerativeAI {
    return new ChatGoogleGenerativeAI({
      model: config?.model ?? this.defaultModel,
      temperature: config?.temperature ?? 0.2,
      maxOutputTokens: config?.maxTokens ?? 4096,
      apiKey: process.env['NEXARQ_GOOGLE_API_KEY'],
    })
  }

  async listModels(): Promise<string[]> {
    return PROVIDER_MODELS.google
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
