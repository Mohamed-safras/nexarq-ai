import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import type { IgnoreStore } from '@nexarq/agent-runtime'

interface IgnoreEntry {
  fingerprint: string
  reason?: string
  ignoredAt: string
}

interface IgnoreFile {
  version: 1
  ignored: IgnoreEntry[]
}

const IGNORE_FILENAME = '.nexarq/ignore.json'

/**
 * File-based ignore store committed to the repo so the whole team shares it.
 * Format: .nexarq/ignore.json
 */
export function createIgnoreStore(workingDirectory: string): IgnoreStore {
  const filePath = join(workingDirectory, IGNORE_FILENAME)

  function load(): IgnoreFile {
    if (!existsSync(filePath)) return { version: 1, ignored: [] }
    try {
      return JSON.parse(readFileSync(filePath, 'utf-8')) as IgnoreFile
    } catch {
      return { version: 1, ignored: [] }
    }
  }

  function save(data: IgnoreFile): void {
    mkdirSync(dirname(filePath), { recursive: true })
    writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n', 'utf-8')
  }

  return {
    isIgnored(fingerprint) {
      const data = load()
      return data.ignored.some((entry) => entry.fingerprint === fingerprint)
    },

    ignore(fingerprint, reason) {
      const data = load()
      if (data.ignored.some((entry) => entry.fingerprint === fingerprint)) return
      data.ignored.push({
        fingerprint,
        ...(reason ? { reason } : {}),
        ignoredAt: new Date().toISOString(),
      })
      save(data)
    },

    list() {
      return load().ignored
    },
  }
}
