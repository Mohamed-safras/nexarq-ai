import type { FindingSeverity } from '../types'

export interface ParsedFinding {
  agentName: string
  file: string
  line: number
  message: string
  suggestion?: string
  severity: FindingSeverity
}
