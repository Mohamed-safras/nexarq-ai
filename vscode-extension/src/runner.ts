import { spawn } from 'node:child_process'
import type { ParsedFinding, ReviewRun, FindingSeverity } from './types.ts'

const SEVERITY_HEADER_PATTERN = /^\[(\w+)\s*\]\s+(.+)$/
const FINDING_PATTERN = /^FINDING:\s+(\S+?):(\d+)\s+[—–-]+\s+(.+)$/
const SUGGESTION_PATTERN = /^SUGGESTION:\s+(.+)$/

export interface RunnerOptions {
  cliPath: string
  workingDirectory: string
  mode: string
}

export function runNexarqReview(options: RunnerOptions): Promise<ReviewRun> {
  return new Promise((resolve, reject) => {
    const startTime = Date.now()
    const output: string[] = []

    const childProcess = spawn(options.cliPath, ['run', '--mode', options.mode, '--hook'], {
      cwd: options.workingDirectory,
      env: process.env,
      shell: true,
    })

    childProcess.stdout.on('data', (chunk: Buffer) => output.push(chunk.toString()))
    childProcess.stderr.on('data', (chunk: Buffer) => output.push(chunk.toString()))

    childProcess.on('error', (processError) => reject(processError))

    childProcess.on('close', () => {
      const fullOutput = output.join('')
      const findings = parseFindings(fullOutput)
      resolve({
        findings,
        durationMs: Date.now() - startTime,
        agentCount: countAgents(fullOutput),
        ranAt: new Date(),
      })
    })
  })
}

function parseFindings(output: string): ParsedFinding[] {
  const findings: ParsedFinding[] = []
  const lines = output.split('\n')
  let currentAgent = 'review'
  let currentSeverity: FindingSeverity = 'info'

  for (let lineIndex = 0; lineIndex < lines.length; lineIndex++) {
    const line = (lines[lineIndex] ?? '').trim()

    const headerMatch = line.match(SEVERITY_HEADER_PATTERN)
    if (headerMatch) {
      currentSeverity = normalizeSeverity(headerMatch[1] ?? '')
      currentAgent = (headerMatch[2] ?? '').toLowerCase().replace(/\s+/g, '-')
      continue
    }

    const findingMatch = line.match(FINDING_PATTERN)
    if (!findingMatch) continue

    const filePath = findingMatch[1] ?? ''
    const lineNumber = parseInt(findingMatch[2] ?? '0', 10)
    const message = (findingMatch[3] ?? '').trim()

    let suggestion: string | undefined
    const nextLine = (lines[lineIndex + 1] ?? '').trim()
    const suggestionMatch = nextLine.match(SUGGESTION_PATTERN)
    if (suggestionMatch) {
      suggestion = (suggestionMatch[1] ?? '').trim()
      lineIndex++
    }

    findings.push({
      agentName: currentAgent,
      file: filePath,
      line: lineNumber,
      message,
      suggestion,
      severity: currentSeverity,
    })
  }

  return findings
}

function normalizeSeverity(raw: string): FindingSeverity {
  const lower = raw.toLowerCase()
  if (lower === 'critical') return 'critical'
  if (lower === 'high') return 'high'
  if (lower === 'medium') return 'medium'
  if (lower === 'low') return 'low'
  return 'info'
}

function countAgents(output: string): number {
  const agentMatches = output.match(/✓\s+\w/g)
  return agentMatches ? agentMatches.length : 0
}
