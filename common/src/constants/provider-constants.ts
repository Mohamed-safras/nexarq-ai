import type { ProviderName } from '../types/agent-types.ts'
import type { AgentMode } from '../types/agent-types.ts'

export const DEFAULT_PROVIDER: ProviderName = 'ollama'

export const PROVIDER_MODELS: Record<ProviderName, string[]> = {
  ollama:    ['minimax-m2.7:cloud', 'kimi-k2:cloud', 'qwen3.5:4b', 'qwen2.5-coder', 'deepseek-coder-v2', 'llama3.2', 'codellama'],
  openai:    ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
  anthropic: ['claude-opus-4-6', 'claude-sonnet-4-6', 'claude-haiku-4-5-20251001'],
  google:    ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash'],
  // MiniMax M2.5 — ultra-cheap coding model used by Codebuff free tier
  // ~$0.10/1M input, $0.11/1M output — 30x cheaper than GPT-4o
  minimax:   ['MiniMax-M1', 'MiniMax-Text-01'],
}

export const PROVIDER_DEFAULT_MODELS: Record<ProviderName, string> = {
  ollama:    'minimax-m2.7:cloud',
  openai:    'gpt-4o',
  anthropic: 'claude-sonnet-4-6',
  google:    'gemini-2.5-flash',
  minimax:   'MiniMax-M1',
}

// Cost per 1k tokens in USD
export const PROVIDER_COST_PER_1K_TOKENS: Record<ProviderName, { input: number; output: number }> = {
  ollama:    { input: 0,        output: 0 },
  openai:    { input: 0.005,    output: 0.015 },
  anthropic: { input: 0.003,    output: 0.015 },
  google:    { input: 0.00125,  output: 0.005 },
  minimax:   { input: 0.0001,   output: 0.00011 },
}

export const OLLAMA_DEFAULT_URL   = 'http://localhost:11434'
export const MINIMAX_DEFAULT_URL  = 'https://api.minimax.io/v1'

/**
 * Model selection by mode — maps AgentMode to the cheapest capable model
 * per provider. Startup-friendly: defaults push toward free/cheap models.
 *
 * fast  → cheapest, fastest — for pre-push hooks and watch mode
 * smart → balanced cost/quality — default for post-commit
 * deep  → best quality — for PR reviews and on-demand
 */
export const MODE_MODELS: Record<ProviderName, Record<AgentMode, string>> = {
  ollama: {
    fast:  'minimax-m2.7:cloud',
    smart: 'minimax-m2.7:cloud',
    deep:  'kimi-k2:cloud',
    auto:  'minimax-m2.7:cloud',
  },
  openai: {
    fast:  'gpt-4o-mini',   // $0.15/1M — 20x cheaper than gpt-4o
    smart: 'gpt-4o-mini',
    deep:  'gpt-4o',
    auto:  'gpt-4o-mini',
  },
  anthropic: {
    fast:  'claude-haiku-4-5-20251001',  // $0.25/1M — cheapest Claude
    smart: 'claude-sonnet-4-6',
    deep:  'claude-opus-4-6',
    auto:  'claude-sonnet-4-6',
  },
  google: {
    fast:  'gemini-2.0-flash',   // $0.075/1M — very cheap
    smart: 'gemini-2.5-flash',
    deep:  'gemini-2.5-pro',
    auto:  'gemini-2.5-flash',
  },
  minimax: {
    fast:  'MiniMax-M1',
    smart: 'MiniMax-M1',
    deep:  'MiniMax-Text-01',
    auto:  'MiniMax-M1',
  },
}

/**
 * Max tokens to send per agent in each mode.
 * Keeps costs predictable — huge diffs are truncated before hitting the LLM.
 */
export const MODE_MAX_DIFF_TOKENS: Record<AgentMode, number> = {
  fast:  2_000,
  smart: 6_000,
  deep:  16_000,
  auto:  6_000,
}

/**
 * Max output tokens the LLM may generate per agent per mode.
 * Shorter budgets finish faster; deep mode unlocks full verbosity.
 */
export const MODE_MAX_OUTPUT_TOKENS: Record<AgentMode, number> = {
  fast:  512,
  smart: 1_024,
  deep:  4_096,
  auto:  1_024,
}
