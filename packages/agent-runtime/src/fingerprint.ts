import type { AgentFinding } from '@nexarq/common/interfaces'

/**
 * Produces a stable fingerprint for a finding so identical issues are not
 * reported on every commit. The fingerprint is based on:
 *   - agent name (who found it)
 *   - severity
 *   - title (normalised — stripped of line numbers / hashes)
 *   - file path (if present)
 *
 * We intentionally exclude the full description and line number so the
 * fingerprint survives minor diffs / reformats.
 */
export function fingerprintFinding(agentName: string, finding: AgentFinding): string {
  const normalisedTitle = finding.title
    .replace(/\b\d+\b/g, '')   // strip bare numbers (line refs)
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()

  const raw = [
    agentName,
    finding.severity,
    normalisedTitle,
    finding.file ?? '',
  ].join('\x00')

  return stableHash(raw)
}

/** djb2 hash — fast, no dependencies, good enough for dedup keys */
function stableHash(str: string): string {
  let hash = 5381
  for (let index = 0; index < str.length; index++) {
    hash = ((hash << 5) + hash) ^ str.charCodeAt(index)
    hash = hash >>> 0 // keep unsigned 32-bit
  }
  return hash.toString(16).padStart(8, '0')
}

export interface IgnoreStore {
  /** Returns true if this fingerprint should be suppressed */
  isIgnored(fingerprint: string): boolean
  /** Persist a new ignore entry */
  ignore(fingerprint: string, reason?: string): void
  /** List all ignored fingerprints with metadata */
  list(): Array<{ fingerprint: string; reason?: string; ignoredAt: string }>
}
