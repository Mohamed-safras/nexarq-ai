import type { AgentTier, ChangeType, Severity } from '../../types/agent-types.ts'
import type { AgentFinding } from './agent-finding.ts'

/**
 * Hints that describe when this agent should be auto-selected.
 * The selector reads these instead of maintaining a hardcoded dispatch map —
 * agents are self-describing about when they're relevant.
 *
 * Inspired by Codebuff's spawnerPrompt pattern.
 */
export interface AgentSelectionHints {
  changeTypes?: ChangeType[]
  filePaths?: string[]
  diffContent?: string[]
  minDiffLines?: number
}

export interface AgentDefinition {
  name: string
  displayName: string
  description: string
  severity: Severity
  tier: AgentTier
  systemPrompt: string
  buildPrompt: (diff: string, language: string, context?: string) => string
  selectionHints?: AgentSelectionHints
  parseFindingsFromOutput?: (output: string) => AgentFinding[]
  usesExtendedThinking?: boolean
}
