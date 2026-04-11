import type { ChangeType } from '../../types/agent-types.js'
import type { FileDiff } from './file-diff.js'

export interface DiffResult {
  commitHash?: string
  commitMessage?: string
  author?: string
  timestamp?: string
  files: FileDiff[]
  rawDiff: string
  totalAdded: number
  totalRemoved: number
  changeType: ChangeType
  repoType: string
  primaryLanguage: string
}
