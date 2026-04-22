import type { AgentFinding } from '@nexarq/common/interfaces'
import type { Severity } from '@nexarq/common/types'

const SEVERITY_HEADER_PATTERN = /^\[\s*(\w+)\s*\]\s+(.+)$/
const FINDING_PATTERN = /^FINDING:\s+(\S+?):(\d+)\s+[—–-]+\s+(.+)$/
const SUGGESTION_PATTERN = /^SUGGESTION:\s+(.+)$/

export interface AgentBlock {
  agentName: string
  severity: Severity
  findings: AgentFinding[]
}

export function parseCliOutput(rawOutput: string): AgentBlock[] {
  const blocks: AgentBlock[] = []
  const lines = rawOutput.split('\n')

  let currentAgentName = 'review'
  let currentSeverity: Severity = 'info'
  let currentFindings: AgentFinding[] = []

  function commitBlock(): void {
    if (currentFindings.length > 0) {
      blocks.push({ agentName: currentAgentName, severity: currentSeverity, findings: [...currentFindings] })
      currentFindings = []
    }
  }

  for (let lineIndex = 0; lineIndex < lines.length; lineIndex++) {
    const line = (lines[lineIndex] ?? '').trim()

    const headerMatch = line.match(SEVERITY_HEADER_PATTERN)
    if (headerMatch) {
      commitBlock()
      currentSeverity = normalizeSeverity(headerMatch[1] ?? '')
      currentAgentName = (headerMatch[2] ?? '').toLowerCase().replace(/\s+/g, '-')
      continue
    }

    const findingMatch = line.match(FINDING_PATTERN)
    if (!findingMatch) continue

    const finding: AgentFinding = {
      file: findingMatch[1] ?? '',
      line: parseInt(findingMatch[2] ?? '0', 10),
      message: (findingMatch[3] ?? '').trim(),
      severity: currentSeverity,
    }

    const nextLine = (lines[lineIndex + 1] ?? '').trim()
    const suggestionMatch = nextLine.match(SUGGESTION_PATTERN)
    if (suggestionMatch) {
      finding.suggestion = (suggestionMatch[1] ?? '').trim()
      lineIndex++
    }

    currentFindings.push(finding)
  }

  commitBlock()
  return blocks
}

function normalizeSeverity(raw: string): Severity {
  const lower = raw.toLowerCase()
  const severities: Severity[] = ['critical', 'high', 'medium', 'low', 'info']
  return severities.find((severity) => severity === lower) ?? 'info'
}
