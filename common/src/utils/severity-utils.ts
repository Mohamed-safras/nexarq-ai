import type { Severity } from '../types/agent-types.ts'
import { SEVERITY_ORDER } from '../constants/agent-constants.ts'

export function compareSeverity(severityA: Severity, severityB: Severity): number {
  return SEVERITY_ORDER[severityB] - SEVERITY_ORDER[severityA]
}

export function maxSeverity(severities: Severity[]): Severity {
  if (severities.length === 0) return 'info'
  return severities.reduce((highestSeverity, currentSeverity) =>
    SEVERITY_ORDER[currentSeverity] > SEVERITY_ORDER[highestSeverity]
      ? currentSeverity
      : highestSeverity
  )
}

export function isHighPriority(severity: Severity): boolean {
  return severity === 'critical' || severity === 'high'
}
