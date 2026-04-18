import { NextRequest, NextResponse } from 'next/server'

/**
 * GET /api/v1/trends
 *
 * Returns security finding trends over time for a repo.
 * Powers the web dashboard trend chart.
 *
 * MVP: in-memory store. Production: replace with Drizzle DB queries.
 *
 * Revenue angle: trends are visible in the web dashboard (ad-funded).
 * Enterprise customers get team-wide trends + Slack alerts.
 */

interface TrendDataPoint {
  date: string        // ISO date
  critical: number
  high: number
  medium: number
  low: number
  info: number
  tokensUsed: number
  estimatedCostUsd: number
  agentsRun: number
}

interface RunRecord {
  repo: string
  branch?: string
  timestamp: string
  summary: {
    critical: number
    high: number
    medium: number
    low: number
    info: number
    tokensUsed: number
    estimatedCostUsd: number
    agentsRun: string[]
  }
}

// In-memory store for MVP — swap with DB in production
const runHistory: RunRecord[] = []

export function recordRun(record: RunRecord): void {
  runHistory.push(record)
  // Cap in-memory history at 10k records to prevent leaks
  if (runHistory.length > 10_000) runHistory.splice(0, runHistory.length - 10_000)
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  const { searchParams } = new URL(request.url)
  const repo   = searchParams.get('repo')
  const days   = Math.min(parseInt(searchParams.get('days') ?? '30', 10), 90)
  const branch = searchParams.get('branch') ?? undefined

  if (!repo) {
    return NextResponse.json({ error: 'repo parameter required' }, { status: 400 })
  }

  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - days)

  const filtered = runHistory.filter((record) => {
    if (record.repo !== repo) return false
    if (branch && record.branch !== branch) return false
    return new Date(record.timestamp) >= cutoff
  })

  // Aggregate by day
  const byDay = new Map<string, TrendDataPoint>()

  for (const record of filtered) {
    const day = record.timestamp.slice(0, 10) // YYYY-MM-DD
    const existing = byDay.get(day) ?? {
      date: day,
      critical: 0, high: 0, medium: 0, low: 0, info: 0,
      tokensUsed: 0, estimatedCostUsd: 0, agentsRun: 0,
    }
    existing.critical         += record.summary.critical
    existing.high             += record.summary.high
    existing.medium           += record.summary.medium
    existing.low              += record.summary.low
    existing.info             += record.summary.info
    existing.tokensUsed       += record.summary.tokensUsed
    existing.estimatedCostUsd += record.summary.estimatedCostUsd
    existing.agentsRun        += record.summary.agentsRun.length
    byDay.set(day, existing)
  }

  const trend = [...byDay.values()].sort((dataA, dataB) => dataA.date.localeCompare(dataB.date))

  // Security posture score: 100 - weighted penalty
  const latest = trend.at(-1)
  const score = latest
    ? Math.max(0, 100 - latest.critical * 20 - latest.high * 10 - latest.medium * 3 - latest.low * 1)
    : 100

  return NextResponse.json({
    repo,
    days,
    score,
    trend,
    totalRuns: filtered.length,
  })
}
