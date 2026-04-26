import { spawn } from 'node:child_process'
import type { ReviewRun, AgentResult } from '@nexarq/common/interfaces'
import { parseCliOutput } from './output-parser'
import { buildRunSummary } from './summary-builder'

export interface CliRunnerOptions {
  cliPath: string
  workingDirectory: string
  mode: string
}

export async function runNexarqCli(options: CliRunnerOptions): Promise<ReviewRun> {
  const startTime = Date.now()
  const rawOutput = await spawnCliProcess(options)
  const agentBlocks = parseCliOutput(rawOutput)

  const results: AgentResult[] = agentBlocks.map((block) => ({
    agentName: block.agentName,
    severity: block.severity,
    output: block.findings
      .map((finding) => `FINDING: ${finding.file}:${finding.line} — ${finding.message}`)
      .join('\n'),
    findings: block.findings,
    warnings: [],
    tokenUsage: { promptTokens: 0, completionTokens: 0, totalTokens: 0 },
    latencyMs: 0,
    cached: false,
  }))

  return {
    results,
    summary: buildRunSummary(results),
    durationMs: Date.now() - startTime,
    ranAt: new Date().toISOString(),
  }
}

function spawnCliProcess(options: CliRunnerOptions): Promise<string> {
  return new Promise((resolve, reject) => {
    const outputChunks: string[] = []

    const childProcess = spawn(
      options.cliPath,
      ['run', '--mode', options.mode, '--hook'],
      { cwd: options.workingDirectory, env: process.env, shell: true }
    )

    childProcess.stdout.on('data', (chunk: Buffer) => outputChunks.push(chunk.toString()))
    childProcess.stderr.on('data', (chunk: Buffer) => outputChunks.push(chunk.toString()))
    childProcess.on('error', (processError) => reject(processError))
    childProcess.on('close', () => resolve(outputChunks.join('')))
  })
}
