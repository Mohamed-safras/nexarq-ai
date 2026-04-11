export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info'

export type AgentMode = 'fast' | 'smart' | 'deep' | 'auto'

export type AgentTier = 1 | 2 | 3

export type ProviderName = 'ollama' | 'openai' | 'anthropic' | 'google' | 'minimax'

export type ChangeType =
  | 'feature'
  | 'bugfix'
  | 'refactor'
  | 'docs'
  | 'test'
  | 'performance'
  | 'security'
  | 'database'
  | 'general'
