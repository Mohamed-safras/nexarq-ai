import { execSync } from 'node:child_process'
import { runOrchestrator, type TriggerSource } from '@nexarq/agent-runtime'
import type { ProviderName } from '@nexarq/common/types'

// GitHub Actions core API — reads inputs, sets outputs, fails the job
function getInput(name: string, defaultValue = ''): string {
  return process.env[`INPUT_${name.toUpperCase().replace(/-/g, '_')}`] ?? defaultValue
}
function setOutput(name: string, value: string | number): void {
  process.stdout.write(`::set-output name=${name}::${value}\n`)
}
function setFailed(message: string): void {
  process.stdout.write(`::error::${message}\n`)
  process.exit(1)
}
function info(message: string): void {
  console.log(message)
}

async function run(): Promise<void> {
  // ── Inputs ────────────────────────────────────────────────────────────────
  const provider    = getInput('provider', 'google') as ProviderName
  const model       = getInput('model') || undefined
  const mode        = (getInput('mode', 'smart') as 'fast' | 'smart' | 'deep')
  const agentsInput = getInput('agents')
  const agents      = agentsInput ? agentsInput.split(',').map((s) => s.trim()) : undefined
  const failOn      = getInput('fail-on', 'high')
  const postComment = getInput('post-comment', 'true') === 'true'
  const githubToken = getInput('github-token')

  // ── Set provider API key from action input ─────────────────────────────
  const keyMap: Partial<Record<ProviderName, string>> = {
    anthropic: getInput('anthropic-api-key'),
    openai:    getInput('openai-api-key'),
    google:    getInput('google-api-key'),
    minimax:   getInput('minimax-api-key'),
  }
  const apiKey = keyMap[provider]
  if (apiKey) {
    const envKey: Partial<Record<ProviderName, string>> = {
      anthropic: 'NEXARQ_ANTHROPIC_API_KEY',
      openai:    'NEXARQ_OPENAI_API_KEY',
      google:    'NEXARQ_GOOGLE_API_KEY',
      minimax:   'NEXARQ_MINIMAX_API_KEY',
    }
    const envName = envKey[provider]
    if (envName) process.env[envName] = apiKey
  }

  // ── Get PR diff ───────────────────────────────────────────────────────────
  info('Extracting diff...')
  let rawDiff = ''

  const eventName = process.env['GITHUB_EVENT_NAME'] ?? ''
  const isPR = eventName === 'pull_request' || eventName === 'pull_request_target'
  const isMerge = eventName === 'push'

  if (isPR) {
    try {
      rawDiff = execSync('git diff origin/main...HEAD', { encoding: 'utf-8' }).trim()
    } catch {
      rawDiff = execSync('git diff HEAD~1 HEAD', { encoding: 'utf-8' }).trim()
    }
  } else if (isMerge) {
    rawDiff = execSync('git diff HEAD~1 HEAD', { encoding: 'utf-8' }).trim()
  }

  if (!rawDiff) {
    info('No diff found — skipping review.')
    setOutput('findings-count', 0)
    setOutput('critical-count', 0)
    setOutput('high-count', 0)
    setOutput('summary', '{}')
    return
  }

  // ── Run agents ────────────────────────────────────────────────────────────
  const triggerSource: TriggerSource = isPR ? 'pr-review' : 'post-commit'
  info(`Running Nexarq review (${mode} mode, ${provider})...`)

  const result = await runOrchestrator({
    task: 'Review the following diff',
    diffResult: {
      rawDiff,
      files: [],
      totalAdded: 0,
      totalRemoved: 0,
      changeType: 'general',
      repoType: 'unknown',
      primaryLanguage: 'unknown',
    },
    triggerSource,
    runConfig: {
      provider,
      ...(model   ? { model }   : {}),
      mode,
      ...(agents  ? { agents }  : {}),
    },
  })

  const { summary, results } = result
  info(`Review complete: ${summary.critical}c ${summary.high}h ${summary.medium}m ${summary.low}l`)

  // ── Set outputs ───────────────────────────────────────────────────────────
  setOutput('findings-count', summary.totalFindings)
  setOutput('critical-count', summary.critical)
  setOutput('high-count', summary.high)
  setOutput('summary', JSON.stringify(summary))

  // ── Post PR comment ───────────────────────────────────────────────────────
  if (postComment && isPR && githubToken) {
    const prNumber = JSON.parse(process.env['GITHUB_EVENT_PATH']
      ? require('node:fs').readFileSync(process.env['GITHUB_EVENT_PATH'], 'utf-8')
      : '{}')?.number

    if (prNumber) {
      const repo   = process.env['GITHUB_REPOSITORY'] ?? ''
      const apiUrl = `https://api.github.com/repos/${repo}/issues/${prNumber}/comments`

      const lines: string[] = [
        '## Nexarq Code Review',
        '',
        `| Severity | Count |`,
        `|----------|-------|`,
        `| 🔴 Critical | ${summary.critical} |`,
        `| 🟠 High     | ${summary.high} |`,
        `| 🟡 Medium   | ${summary.medium} |`,
        `| 🔵 Low      | ${summary.low} |`,
        `| ℹ️ Info     | ${summary.info} |`,
        '',
      ]

      for (const agentResult of results) {
        if (agentResult.findings.length === 0) continue
        lines.push(`### ${agentResult.agentName}`)
        for (const finding of agentResult.findings.slice(0, 5)) {
          const sev = finding.severity ? `[${finding.severity.toUpperCase()}] ` : ''
          lines.push(`- **${sev}**${finding.message}`)
          if (finding.file) lines.push(`  > \`${finding.file}${finding.line ? `:${finding.line}` : ''}\``)
        }
        lines.push('')
      }

      lines.push('---')
      lines.push('*Powered by [Nexarq](https://nexarq.dev) — free AI code review*')

      await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${githubToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ body: lines.join('\n') }),
      })
    }
  }

  // ── Fail check ────────────────────────────────────────────────────────────
  const severityOrder = ['none', 'info', 'low', 'medium', 'high', 'critical']
  const failThreshold = severityOrder.indexOf(failOn)

  if (failThreshold > 0) {
    const shouldFail =
      (failOn === 'critical' && summary.critical > 0) ||
      (failOn === 'high'     && summary.critical + summary.high > 0) ||
      (failOn === 'medium'   && summary.critical + summary.high + summary.medium > 0)

    if (shouldFail) {
      setFailed(
        `Nexarq found ${summary.critical} critical, ${summary.high} high, ${summary.medium} medium severity issues.`
      )
    }
  }
}

run().catch((error: unknown) => {
  setFailed(error instanceof Error ? error.message : String(error))
})
