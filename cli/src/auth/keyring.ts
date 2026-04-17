import type { ProviderName } from '@nexarq/common/types'

const SERVICE_NAME = 'nexarq'

export async function storeApiKey(provider: ProviderName, apiKey: string): Promise<void> {
  try {
    const keytar = await import('keytar')
    await keytar.default.setPassword(SERVICE_NAME, provider, apiKey)
  } catch {
    // Keytar not available — fall back to env var hint
    console.warn(`Could not store key in system keyring. Set NEXARQ_${provider.toUpperCase()}_API_KEY instead.`)
  }
}

export async function getApiKey(provider: ProviderName): Promise<string | null> {
  // Env var always wins (useful in CI)
  const envKey = process.env[`NEXARQ_${provider.toUpperCase()}_API_KEY`]
  if (envKey) return envKey

  try {
    const keytar = await import('keytar')
    return await keytar.default.getPassword(SERVICE_NAME, provider)
  } catch {
    return null
  }
}

export async function deleteApiKey(provider: ProviderName): Promise<void> {
  try {
    const keytar = await import('keytar')
    await keytar.default.deletePassword(SERVICE_NAME, provider)
  } catch {
    // Silently ignore if keytar unavailable
  }
}
