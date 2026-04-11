import { existsSync, readFileSync } from 'node:fs'
import { join, resolve } from 'node:path'

const KNOWLEDGE_FILENAMES = [
  'NEXARQ.md',
  '.nexarq/knowledge.md',
  '.nexarq/NEXARQ.md',
]

const MAX_KNOWLEDGE_BYTES = 8_000 // ~2k tokens — keep it cheap

/**
 * Loads the project knowledge file from the working directory.
 * The knowledge file lets teams inject repo-specific context into every agent:
 *   - Architecture decisions
 *   - Off-limits patterns ("we use X not Y")
 *   - Domain-specific security rules
 *   - Known tech debt to ignore
 *
 * Create: echo "## Context\nWe use Drizzle not Prisma." > NEXARQ.md
 */
export function loadKnowledgeFile(workingDirectory: string): string | null {
  const rootDir = resolve(workingDirectory)

  for (const filename of KNOWLEDGE_FILENAMES) {
    const fullPath = join(rootDir, filename)
    if (existsSync(fullPath)) {
      try {
        const raw = readFileSync(fullPath, 'utf-8')
        const trimmed = raw.trim()
        if (!trimmed) return null

        // Truncate to avoid blowing up token budgets on every agent call
        if (Buffer.byteLength(trimmed, 'utf-8') > MAX_KNOWLEDGE_BYTES) {
          const truncated = trimmed.slice(0, MAX_KNOWLEDGE_BYTES)
          const lastNewline = truncated.lastIndexOf('\n')
          return lastNewline > 0
            ? truncated.slice(0, lastNewline) + '\n\n[...truncated]'
            : truncated + '\n\n[...truncated]'
        }

        return trimmed
      } catch {
        return null
      }
    }
  }

  return null
}

export function formatKnowledgeBlock(knowledge: string): string {
  return `\n\n--- PROJECT KNOWLEDGE ---\n${knowledge}\n--- END PROJECT KNOWLEDGE ---`
}
