import { ChatAnthropic } from '@langchain/anthropic'
import type { IProvider, ProviderConfig } from './base-provider.ts'
import { PROVIDER_DEFAULT_MODELS, PROVIDER_MODELS } from '@nexarq/common/constants'

export class AnthropicProvider implements IProvider {
  readonly providerName = 'anthropic' as const
  readonly defaultModel = PROVIDER_DEFAULT_MODELS.anthropic

  buildModel(config?: ProviderConfig): ChatAnthropic {
    return new ChatAnthropic({
      model: config?.model ?? this.defaultModel,
      temperature: config?.temperature ?? 0.2,
      maxTokens: config?.maxTokens ?? 4096,
      ...(process.env['NEXARQ_ANTHROPIC_API_KEY'] ? { apiKey: process.env['NEXARQ_ANTHROPIC_API_KEY'] } : {}),
    })
  }

  async listModels(): Promise<string[]> {
    return PROVIDER_MODELS.anthropic
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
