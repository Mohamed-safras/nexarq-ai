import { execSync } from 'child_process'
import type { TriggerSource } from '@nexarq/agent-runtime'

const MAX_DIFF_LINES = 5_000

export async function extractDiff(triggerSource: TriggerSource): Promise<string> {
  if (process.env['NEXARQ_SKIP'] === '1') return ''

  const rawDiff = triggerSource === 'pre-push'
    ? getStagedDiff()
    : getLastCommitDiff()

  const lines = rawDiff.split('\n')
  if (lines.length > MAX_DIFF_LINES) {
    return lines.slice(0, MAX_DIFF_LINES).join('\n') + '\n... [diff truncated]'
  }
  return rawDiff
}

function getLastCommitDiff(): string {
  try {
    return execSync('git diff HEAD~1 HEAD', {
      encoding: 'utf-8',
      timeout: 10_000,
      stdio: ['pipe', 'pipe', 'pipe'],
    })
  } catch {
    // Fallback for first commit (no parent)
    try {
      return execSync('git show --format="" HEAD', {
        encoding: 'utf-8',
        timeout: 10_000,
        stdio: ['pipe', 'pipe', 'pipe'],
      })
    } catch {
      throw new Error('Could not extract git diff. Are you inside a git repository?')
    }
  }
}

function getStagedDiff(): string {
  try {
    return execSync('git diff --cached', {
      encoding: 'utf-8',
      timeout: 10_000,
      stdio: ['pipe', 'pipe', 'pipe'],
    })
  } catch {
    throw new Error('Could not extract staged diff.')
  }
}
