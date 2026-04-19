import { tool } from '@langchain/core/tools'
import { z } from 'zod'

const MAX_DOCS_CHARS   = 6_000
const FETCH_TIMEOUT_MS = 12_000

// Session-level cache — avoids re-fetching same library+topic within one session
const docsCache = new Map<string, string>()

/**
 * Search the web for the official docs page for a given library and topic,
 * then fetch it via Jina Reader (converts any URL to clean markdown).
 *
 * Always dynamic — no predefined URL map. Works for any library, any version.
 */
async function findAndFetchDocs(library: string, topic: string): Promise<string> {
  // ── Step 1: find the best docs URL via Brave Search ───────────────────────
  const apiKey = process.env['NEXARQ_BRAVE_API_KEY']
  if (!apiKey) {
    return '[DOCS UNAVAILABLE] Set NEXARQ_BRAVE_API_KEY to enable automatic docs lookup.'
  }

  const query   = encodeURIComponent(`${library} ${topic} official documentation API reference`)
  const searchUrl = `https://api.search.brave.com/res/v1/web/search?q=${query}&count=5`

  const searchRes = await fetch(searchUrl, {
    headers: { 'X-Subscription-Token': apiKey, 'Accept': 'application/json' },
    signal: AbortSignal.timeout(8_000),
  })
  if (!searchRes.ok) throw new Error(`Search HTTP ${searchRes.status}`)

  type BraveResult = { url: string; title: string; description?: string }
  type BraveResponse = { web?: { results?: BraveResult[] } }
  const data = await searchRes.json() as BraveResponse
  const results = data.web?.results ?? []

  if (results.length === 0) return `No docs found for "${library} ${topic}".`

  // Prefer official docs: domains containing /docs/, /api/, or starting with docs.*
  const ranked = [...results].sort((a, b) => {
    const score = (r: BraveResult) => {
      let s = 0
      if (r.url.includes('/docs') || r.url.includes('/api/') || r.url.includes('/reference/')) s += 3
      if (r.url.startsWith('https://docs.')) s += 2
      if (r.url.endsWith('.dev') || r.url.endsWith('.io')) s += 1
      if (r.title.toLowerCase().includes(library.toLowerCase())) s += 2
      return s
    }
    return score(b) - score(a)
  })

  const bestUrl = ranked[0]!.url

  // ── Step 2: fetch the page via Jina Reader (clean markdown, token-efficient) ─
  const jinaUrl = `https://r.jina.ai/${bestUrl}`
  const jinaHeaders: Record<string, string> = { 'Accept': 'text/plain' }

  const jinaKey = process.env['NEXARQ_JINA_API_KEY']
  if (jinaKey) jinaHeaders['Authorization'] = `Bearer ${jinaKey}`

  const docsRes = await fetch(jinaUrl, {
    headers: jinaHeaders,
    signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
  })
  if (!docsRes.ok) throw new Error(`Jina HTTP ${docsRes.status} for ${bestUrl}`)

  const rawMarkdown = (await docsRes.text()).trim()

  // ── Step 3: focus on the relevant section, then truncate ─────────────────
  const focused = focusOnTopic(rawMarkdown, topic)
  const result  = focused.length > MAX_DOCS_CHARS
    ? focused.slice(0, MAX_DOCS_CHARS) + `\n\n... [truncated — source: ${bestUrl}]`
    : `${focused}\n\n[Source: ${bestUrl}]`

  return result
}

/**
 * Finds the heading most relevant to `topic` and returns the section beneath it.
 * Keeps token cost low — returns ~80 lines around the best match, not the full page.
 */
function focusOnTopic(markdown: string, topic: string): string {
  const topicWords = topic.toLowerCase().split(/\s+/)
  const lines = markdown.split('\n')

  let bestIdx = -1
  let bestScore = 0

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i] ?? ''
    if (!line.startsWith('#')) continue
    const lineLower = line.toLowerCase()
    const score = topicWords.filter((w) => lineLower.includes(w)).length
    if (score > bestScore) { bestScore = score; bestIdx = i }
  }

  if (bestIdx === -1 || bestScore === 0) return markdown // No focused section found

  const section = lines.slice(bestIdx, bestIdx + 80).join('\n')
  return section.length > 4_000 ? section.slice(0, 4_000) + '\n... [section truncated]' : section
}

/**
 * Docs tools available to the conversation orchestrator and all coding agents.
 *
 * Automatically searches the web for official docs, converts the page to
 * clean markdown via Jina Reader, and caches results per session.
 * Token cost is ~5× lower than raw HTML for equivalent content.
 */
export function getDocsTools() {
  const readDocsTool = tool(
    async ({ library, topic, url }: { library: string; topic: string; url?: string }): Promise<string> => {
      const cacheKey = `${library.toLowerCase()}:${topic.toLowerCase()}:${url ?? ''}`

      if (docsCache.has(cacheKey)) {
        return `[CACHED]\n${docsCache.get(cacheKey)!}`
      }

      try {
        let result: string

        if (url) {
          // Direct URL provided — skip search, go straight to Jina
          const jinaHeaders: Record<string, string> = { 'Accept': 'text/plain' }
          const jinaKey = process.env['NEXARQ_JINA_API_KEY']
          if (jinaKey) jinaHeaders['Authorization'] = `Bearer ${jinaKey}`

          const res = await fetch(`https://r.jina.ai/${url}`, {
            headers: jinaHeaders,
            signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
          })
          const raw = (await res.text()).trim()
          const focused = focusOnTopic(raw, topic)
          result = focused.length > MAX_DOCS_CHARS
            ? focused.slice(0, MAX_DOCS_CHARS) + `\n\n... [truncated — source: ${url}]`
            : `${focused}\n\n[Source: ${url}]`
        } else {
          result = await findAndFetchDocs(library, topic)
        }

        docsCache.set(cacheKey, result)
        return result
      } catch (err) {
        return `[DOCS ERROR] ${err instanceof Error ? err.message : String(err)}`
      }
    },
    {
      name: 'read_docs',
      description:
        'Automatically search the web and fetch official documentation for any library or framework. ' +
        'Returns clean markdown focused on the requested topic. ' +
        'Use this instead of guessing API signatures — it fetches the real docs. ' +
        'Results are cached per session.',
      schema: z.object({
        library: z.string().describe('Library or framework name, e.g. "express", "react", "drizzle-orm", "langchain"'),
        topic:   z.string().describe('Specific topic or API to look up, e.g. "Router middleware", "useEffect hook", "select query"'),
        url:     z.string().optional().describe('Override: fetch this specific URL directly instead of searching'),
      }),
    }
  )

  return [readDocsTool]
}
