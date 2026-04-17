import type { DiffResult } from '@nexarq/common/interfaces'

/**
 * Builds a minimal DiffResult for passing a raw diff string to runOrchestrator.
 * All structural metadata (files, change counts, repo type) defaults to unknown/empty —
 * the orchestrator derives context from the rawDiff itself.
 */
export function makeDiffResult(rawDiff: string): DiffResult {
  return {
    rawDiff,
    files: [],
    totalAdded: 0,
    totalRemoved: 0,
    changeType: 'general',
    repoType: 'unknown',
    primaryLanguage: 'unknown',
  }
}
