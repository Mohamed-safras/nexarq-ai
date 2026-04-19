/**
 * CLI ad banner system — startup-friendly monetisation.
 *
 * Revenue model:
 *   - CLI ads: ~$2-5 CPM (cost per 1000 impressions)
 *   - At 10k daily active users, 1-in-5 runs shows an ad:
 *     2000 impressions/day × $3 CPM = ~$6/day = ~$180/month
 *   - Scales linearly with users. No code changes needed.
 *
 * Ad sources (by priority):
 *   1. Paid sponsorships (highest CPM — direct deals)
 *   2. Carbon Ads API (developer-focused, ~$3-5 CPM)
 *   3. House ads (nexarq.dev, free tier upsell, 0 cost)
 *
 * Placement rules:
 *   - Show at most 1 ad per run
 *   - Never show in pre-push or hook mode (blocks developer flow)
 *   - Never show if NEXARQ_NO_ADS=1
 *   - Show 1 in every 5 on-demand or chat runs
 */

import chalk from 'chalk'

interface AdSlot {
  headline: string
  url: string
  sponsor: string
}

// House ads — free, always available, promote the product ecosystem
const HOUSE_ADS: AdSlot[] = [
  {
    headline: 'Add Nexarq to GitHub Actions — get AI review on every PR',
    url: 'https://nexarq.dev/github-action',
    sponsor: 'nexarq.dev',
  },
  {
    headline: 'nexarq.dev — free web dashboard for security trend tracking',
    url: 'https://nexarq.dev',
    sponsor: 'nexarq.dev',
  },
  {
    headline: 'Support Nexarq: star the repo or share with a teammate',
    url: 'https://github.com/nexarq/nexarq',
    sponsor: 'nexarq community',
  },
]

let runCount = 0

/**
 * Prints a CLI ad banner if conditions are met.
 * Returns true if an ad was shown.
 */
export async function maybeShowCliAd(triggerSource: string): Promise<boolean> {
  // Never in git hooks — blocks developer flow
  if (triggerSource === 'pre-push' || triggerSource === 'post-commit') return false

  // Env override
  if (process.env['NEXARQ_NO_ADS'] === '1') return false

  runCount++
  if (runCount % 5 !== 0) return false // 1 in 5 runs

  const ad = await fetchAd()
  if (!ad) return false

  console.log()
  console.log(chalk.gray('  ─────────────────────────────────────────────────'))
  console.log(`  ${chalk.bold.cyan('Sponsor:')} ${chalk.white(ad.headline)}`)
  console.log(`           ${chalk.gray(ad.url)}`)
  console.log(`  ${chalk.gray(`via ${ad.sponsor}`)}`)
  console.log(chalk.gray('  ─────────────────────────────────────────────────'))
  console.log()

  return true
}

/**
 * Fetches a paid ad from Carbon Ads, falls back to a house ad.
 * Carbon Ads API: https://carbonads.net/api (requires approval)
 */
async function fetchAd(): Promise<AdSlot | null> {
  const carbonServe    = process.env['CARBON_ADS_SERVE']
  const carbonPlacement = process.env['CARBON_ADS_PLACEMENT']

  if (carbonServe && carbonPlacement) {
    try {
      const response = await fetch(
        `https://srv.carbonads.net/ads/${carbonServe}.json?segment=placement:${carbonPlacement}`,
        { signal: AbortSignal.timeout(2000) }
      )
      if (response.ok) {
        const data = await response.json() as {
          ads?: Array<{ statlink?: string; description?: string; company?: string }>
        }
        const carbonAd = data.ads?.[0]
        if (carbonAd?.statlink && carbonAd.description) {
          return {
            headline: carbonAd.description,
            url: carbonAd.statlink,
            sponsor: carbonAd.company ?? 'carbon ads',
          }
        }
      }
    } catch {
      // Network failure — fall through to house ad
    }
  }

  // House ad fallback
  const index = Math.floor(Math.random() * HOUSE_ADS.length)
  return HOUSE_ADS[index] ?? null
}
