import { NextRequest, NextResponse } from 'next/server'
import { runOrchestrator, buildRunResponse } from '@nexarq/agent-runtime'
import crypto from 'crypto'

const GITHUB_WEBHOOK_SECRET = process.env['NEXARQ_GITHUB_WEBHOOK_SECRET'] ?? ''
const GITHUB_TOKEN          = process.env['NEXARQ_GITHUB_TOKEN'] ?? ''

function verifyGitHubSignature(body: string, signature: string | null): boolean {
  if (!signature || !GITHUB_WEBHOOK_SECRET) return false
  const expectedSignature = 'sha256=' + crypto
    .createHmac('sha256', GITHUB_WEBHOOK_SECRET)
    .update(body)
    .digest('hex')
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expectedSignature)
  )
}

interface PullRequestPayload {
  action: string
  pull_request: {
    number: number
    title: string
    diff_url: string
    head: { sha: string }
    base: { repo: { default_branch: string } }
  }
  repository: { full_name: string }
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const rawBody  = await request.text()
  const signature = request.headers.get('x-hub-signature-256')

  if (!verifyGitHubSignature(rawBody, signature)) {
    return NextResponse.json({ error: 'Invalid signature' }, { status: 401 })
  }

  const event = request.headers.get('x-github-event')
  if (event !== 'pull_request') {
    return NextResponse.json({ message: 'Event ignored' })
  }

  const payload = JSON.parse(rawBody) as PullRequestPayload

  if (!['opened', 'synchronize'].includes(payload.action)) {
    return NextResponse.json({ message: 'Action ignored' })
  }

  // Fetch diff with auth if token available (avoids 60 req/hr anon limit)
  const diffHeaders: Record<string, string> = { Accept: 'application/vnd.github.v3.diff' }
  if (GITHUB_TOKEN) diffHeaders['Authorization'] = `Bearer ${GITHUB_TOKEN}`

  const diffResponse = await fetch(payload.pull_request.diff_url, { headers: diffHeaders })
  if (!diffResponse.ok) {
    return NextResponse.json({ error: 'Failed to fetch diff' }, { status: 502 })
  }
  const diff = await diffResponse.text()

  // Run full pr-review (all tier 1 + 2 agents + meta agents)
  const runResult = await runOrchestrator({
    task: `Review PR #${payload.pull_request.number}: ${payload.pull_request.title}`,
    diffResult: {
      rawDiff: diff,
      files: [],
      totalAdded: diff.split('\n').filter((line) => line.startsWith('+')).length,
      totalRemoved: diff.split('\n').filter((line) => line.startsWith('-')).length,
      changeType: 'general',
      repoType: 'unknown',
      primaryLanguage: 'unknown',
    },
    triggerSource: 'pr-review',
    runConfig: { mode: 'deep' },
  })

  // Post findings as a GitHub PR review comment
  if (GITHUB_TOKEN) {
    await postPrComment(payload.repository.full_name, payload.pull_request.number, runResult)
  }

  return NextResponse.json(buildRunResponse(runResult))
}

async function postPrComment(
  repoFullName: string,
  prNumber: number,
  runResult: Awaited<ReturnType<typeof runOrchestrator>>
): Promise<void> {
  const { summary, results } = runResult

  const lines: string[] = [
    '## Nexarq Code Review',
    '',
    '| Severity | Count |',
    '|----------|-------|',
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
      if (finding.file) {
        lines.push(`  > \`${finding.file}${finding.line ? `:${finding.line}` : ''}\``)
      }
      if (finding.suggestion) {
        lines.push(`  ${finding.suggestion.slice(0, 200)}`)
      }
    }
    if (agentResult.findings.length > 5) {
      lines.push(`  *...and ${agentResult.findings.length - 5} more*`)
    }
    lines.push('')
  }

  lines.push('---')
  lines.push('*Powered by [Nexarq](https://nexarq.dev) — free AI code review*')

  await fetch(`https://api.github.com/repos/${repoFullName}/issues/${prNumber}/comments`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${GITHUB_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ body: lines.join('\n') }),
  })
}
