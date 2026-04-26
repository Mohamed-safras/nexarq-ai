export type FindingSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info'

export interface ParsedFinding {
  agentName: string
  file: string
  line: number
  message: string
  suggestion?: string
  severity: FindingSeverity
}

export interface ReviewRun {
  findings: ParsedFinding[]
  durationMs: number
  agentCount: number
  ranAt: Date
}
