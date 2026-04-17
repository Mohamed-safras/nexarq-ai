import type { AgentMode, Severity } from '../types/agent-types.ts'

export const SEVERITY_ORDER: Record<Severity, number> = {
  critical: 5,
  high: 4,
  medium: 3,
  low: 2,
  info: 1,
}

export const DEFAULT_TIER1_AGENTS = ['security', 'secrets', 'bugs'] as const

export const DEFAULT_MAX_AGENTS = 6

export const DEFAULT_TOOL_CALL_BUDGET = 25

export const DEFAULT_MODE: AgentMode = 'smart'

export const RESULT_CACHE_TTL_HOURS = 24

export const MAX_DIFF_LINES = 5000

export const MAX_CONTEXT_CHARS = 10_000

export const MAX_FILE_CHARS = 4_000

export const MAX_SNIPPET_CHARS = 1_500
