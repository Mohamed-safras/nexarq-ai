/**
 * Credit tracking for cloud/enterprise use.
 *
 * Revenue model (startup-friendly):
 *
 *   Free tier:
 *     - Unlimited local (Ollama) usage — $0 cost to us
 *     - 500 cloud tokens/month via MiniMax (cost to us: ~$0.05/user/month)
 *     - Funded by CLI + web ads
 *
 *   Pro tier ($9/month):
 *     - 100k cloud tokens/month
 *     - Cost to us: ~$1-3/user/month (depends on provider)
 *     - Margin: $6-8/user/month
 *
 *   Enterprise ($99/month/team):
 *     - Unlimited tokens via their own API keys
 *     - SLA, SSO, audit logs, self-host support
 *     - Pure margin — we just host the orchestration
 *
 *   GitHub Action free tier:
 *     - 50 PR reviews/month
 *     - Viral growth driver — every PR shows "Powered by Nexarq"
 *
 * This module tracks usage against limits and enforces quotas.
 * For MVP: implement in-memory only. Persist to DB when ready.
 */

export interface CreditBalance {
  used: number
  limit: number
  resetAt: string // ISO date
  tier: 'free' | 'pro' | 'enterprise'
}

export interface UsageRecord {
  runId: string
  tokensUsed: number
  provider: string
  estimatedCostUsd: number
  timestamp: string
}

// In-memory store for MVP — replace with DB calls in production
const usageLog: UsageRecord[] = []

export function recordUsage(record: UsageRecord): void {
  usageLog.push(record)
}

export function getUsageThisMonth(): number {
  const now = new Date()
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString()
  return usageLog
    .filter((record) => record.timestamp >= monthStart)
    .reduce((total, record) => total + record.tokensUsed, 0)
}

export function getCostThisMonth(): number {
  const now = new Date()
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString()
  return usageLog
    .filter((record) => record.timestamp >= monthStart)
    .reduce((total, record) => total + record.estimatedCostUsd, 0)
}

/**
 * Free tier quota check.
 * Returns true if the user is within the free tier limit.
 * At 500 tokens/month with MiniMax pricing ($0.0001/1k), that's $0.00005/user — essentially free.
 */
export function isWithinFreeQuota(tokensUsed: number): boolean {
  const FREE_TIER_TOKENS_PER_MONTH = 500_000 // ~500k tokens free
  return getUsageThisMonth() + tokensUsed <= FREE_TIER_TOKENS_PER_MONTH
}

export function getFreeBalance(): CreditBalance {
  const now = new Date()
  const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1)
  return {
    used: getUsageThisMonth(),
    limit: 500_000,
    resetAt: nextMonth.toISOString(),
    tier: 'free',
  }
}
