import { ChatOllama } from '@langchain/ollama'
import type { IProvider, ProviderConfig } from './base-provider.ts'
import { PROVIDER_DEFAULT_MODELS, PROVIDER_MODELS, OLLAMA_DEFAULT_URL } from '@nexarq/common/constants'

export class OllamaProvider implements IProvider {
  readonly providerName = 'ollama' as const
  readonly defaultModel = PROVIDER_DEFAULT_MODELS.ollama

  private readonly baseUrl = process.env['NEXARQ_OLLAMA_URL'] ?? OLLAMA_DEFAULT_URL

  buildModel(config?: ProviderConfig): ChatOllama {
    return new ChatOllama({
      model: config?.model ?? this.defaultModel,
      temperature: config?.temperature ?? 0.2,
      numPredict: config?.maxTokens ?? 4096,
      baseUrl: this.baseUrl,
    })
  }

  async listModels(): Promise<string[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/tags`)
      if (!response.ok) return PROVIDER_MODELS.ollama
      const data = await response.json() as { models?: Array<{ name: string }> }
      return data.models?.map((ollamaModel) => ollamaModel.name) ?? PROVIDER_MODELS.ollama
    } catch {
      return PROVIDER_MODELS.ollama
    }
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/tags`)
      return response.ok
    } catch {
      return false
    }
  }
}
