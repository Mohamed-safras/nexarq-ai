import type { ProviderName } from '@nexarq/common/types'
import type { IProvider } from './base-provider.ts'
import { AnthropicProvider } from './anthropic-provider.ts'
import { OpenAIProvider } from './openai-provider.ts'
import { GoogleProvider } from './google-provider.ts'
import { OllamaProvider } from './ollama-provider.ts'
import { MinimaxProvider } from './minimax-provider.ts'

const providerInstanceCache = new Map<ProviderName, IProvider>()

export function getProvider(providerName: ProviderName): IProvider {
  const cached = providerInstanceCache.get(providerName)
  if (cached) return cached

  const provider = buildProvider(providerName)
  providerInstanceCache.set(providerName, provider)
  return provider
}

function buildProvider(providerName: ProviderName): IProvider {
  switch (providerName) {
    case 'anthropic': return new AnthropicProvider()
    case 'openai':    return new OpenAIProvider()
    case 'google':    return new GoogleProvider()
    case 'ollama':    return new OllamaProvider()
    case 'minimax':   return new MinimaxProvider()
  }
}

export function invalidateProvider(providerName?: ProviderName): void {
  if (providerName) {
    providerInstanceCache.delete(providerName)
  } else {
    providerInstanceCache.clear()
  }
}

export async function detectAvailableProviders(): Promise<ProviderName[]> {
  const allProviderNames: ProviderName[] = ['ollama', 'openai', 'anthropic', 'google', 'minimax']

  const healthResults = await Promise.allSettled(
    allProviderNames.map(async (providerName) => {
      const provider = getProvider(providerName)
      const isHealthy = await provider.healthCheck()
      return isHealthy ? providerName : null
    })
  )

  return healthResults
    .filter((result): result is PromiseFulfilledResult<ProviderName> =>
      result.status === 'fulfilled' && result.value !== null
    )
    .map((result) => result.value)
}
