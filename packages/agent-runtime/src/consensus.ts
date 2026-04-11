import type { AgentFinding } from '@nexarq/common/interfaces'
import { fingerprintFinding } from './fingerprint.ts'

/**
 * Multi-model consensus: run the same agent on two different providers,
 * only surface findings that both models agree on.
 *
 * Reduces false positives significantly — if only one model flags something,
 * it's likely a hallucination or low-confidence finding.
 *
 * Cost: 2x single-model cost, but you get ~60% fewer false positives.
 * Use only in `deep` mode or when explicitly requested.
 */
export function intersectFindings(
  agentName: string,
  findingsA: AgentFinding[],
  findingsB: AgentFinding[]
): AgentFinding[] {
  if (findingsA.length === 0 || findingsB.length === 0) return []

  const fingerprintsB = new Set(
    findingsB.map((finding) => fingerprintFinding(agentName, finding))
  )

  return findingsA.filter((finding) => {
    const fp = fingerprintFinding(agentName, finding)
    return fingerprintsB.has(fp)
  })
}

/**
 * Union mode: surface findings from either model (more coverage, more noise).
 * Used when you want maximum detection at the cost of false positives.
 */
export function unionFindings(
  agentName: string,
  findingsA: AgentFinding[],
  findingsB: AgentFinding[]
): AgentFinding[] {
  const seen = new Set<string>()
  const result: AgentFinding[] = []

  for (const finding of [...findingsA, ...findingsB]) {
    const fp = fingerprintFinding(agentName, finding)
    if (!seen.has(fp)) {
      seen.add(fp)
      result.push(finding)
    }
  }

  return result
}
