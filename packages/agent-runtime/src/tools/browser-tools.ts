import { tool } from '@langchain/core/tools'
import { z } from 'zod'

const PAGE_TEXT_MAX_CHARS = 6_000
const NAV_TIMEOUT_MS      = 15_000

type PlaywrightBrowser = {
  newPage: () => Promise<PlaywrightPage>
  close: () => Promise<void>
}
type PlaywrightPage = {
  goto: (url: string, opts?: { timeout?: number; waitUntil?: string }) => Promise<unknown>
  innerText: (selector: string) => Promise<string>
  locator: (selector: string) => { click: () => Promise<void>; fill: (v: string) => Promise<void> }
  screenshot: (opts?: { type?: string }) => Promise<Buffer>
  url: () => string
  title: () => Promise<string>
  content: () => Promise<string>
  waitForLoadState: (state: string, opts?: { timeout?: number }) => Promise<void>
}

let sharedBrowser: PlaywrightBrowser | null = null
let sharedPage:    PlaywrightPage    | null = null

async function getPage(): Promise<{ page: PlaywrightPage; error: null } | { page: null; error: string }> {
  if (!sharedPage) {
    try {
      // Dynamic import — Playwright is an optional dependency
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const pw = await import('playwright') as any
      const chromium = pw.chromium ?? pw.default?.chromium
      if (!chromium) throw new Error('chromium not found in playwright module')

      sharedBrowser = await chromium.launch({ headless: true })
      sharedPage    = await sharedBrowser!.newPage()
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      if (msg.includes('Cannot find module') || msg.includes('MODULE_NOT_FOUND')) {
        return {
          page: null,
          error:
            '[BROWSER UNAVAILABLE] Playwright is not installed.\n' +
            'Run: bun add -d playwright && bunx playwright install chromium',
        }
      }
      return { page: null, error: `[BROWSER ERROR] ${msg}` }
    }
  }
  return { page: sharedPage, error: null }
}

async function safeInnerText(page: PlaywrightPage): Promise<string> {
  try {
    const raw = await page.innerText('body')
    return raw.replace(/\s+/g, ' ').trim().slice(0, PAGE_TEXT_MAX_CHARS)
  } catch {
    // innerText may fail on some pages — fall back to content() and strip tags
    const html = await page.content()
    return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, PAGE_TEXT_MAX_CHARS)
  }
}

/**
 * Browser automation tools for the conversation orchestrator.
 *
 * Uses a shared Playwright Chromium session — one browser, one page,
 * kept alive for the session to minimise startup cost.
 *
 * Playwright is a peer dependency — tools return an install instruction
 * instead of crashing when it is absent.
 *
 * Token efficiency: all page content is returned as plain text, not HTML.
 */
export function getBrowserTools() {
  const openPageTool = tool(
    async ({ url }: { url: string }): Promise<string> => {
      const { page, error } = await getPage()
      if (error) return error
      await page.goto(url, { timeout: NAV_TIMEOUT_MS, waitUntil: 'domcontentloaded' })
      await page.waitForLoadState('networkidle', { timeout: 5_000 }).catch(() => {})
      const text  = await safeInnerText(page)
      const title = await page.title().catch(() => '')
      return `[PAGE: ${title}] ${page.url()}\n\n${text}`
    },
    {
      name: 'open_page',
      description: 'Navigate to a URL and return the page text content. Use for testing live web apps or fetching docs that block bots.',
      schema: z.object({ url: z.string().describe('Full URL to navigate to') }),
    }
  )

  const getPageTextTool = tool(
    async (): Promise<string> => {
      const { page, error } = await getPage()
      if (error) return error
      const text  = await safeInnerText(page)
      const title = await page.title().catch(() => '')
      return `[PAGE: ${title}]\n\n${text}`
    },
    {
      name: 'get_page_text',
      description: 'Return the visible text of the currently open browser page.',
      schema: z.object({}),
    }
  )

  const clickTool = tool(
    async ({ selector }: { selector: string }): Promise<string> => {
      const { page, error } = await getPage()
      if (error) return error
      try {
        await page.locator(selector).click()
        await page.waitForLoadState('networkidle', { timeout: 3_000 }).catch(() => {})
        return `Clicked "${selector}". Current URL: ${page.url()}`
      } catch (err) {
        return `[CLICK ERROR] ${err instanceof Error ? err.message : String(err)}`
      }
    },
    {
      name: 'click_element',
      description: 'Click an element on the current page using a CSS selector or text selector.',
      schema: z.object({ selector: z.string().describe('CSS selector, e.g. "button#submit" or "text=Sign in"') }),
    }
  )

  const fillFormTool = tool(
    async ({ selector, value }: { selector: string; value: string }): Promise<string> => {
      const { page, error } = await getPage()
      if (error) return error
      try {
        await page.locator(selector).fill(value)
        return `Filled "${selector}" with value.`
      } catch (err) {
        return `[FILL ERROR] ${err instanceof Error ? err.message : String(err)}`
      }
    },
    {
      name: 'fill_form',
      description: 'Fill a form input on the current page.',
      schema: z.object({
        selector: z.string().describe('CSS selector for the input field'),
        value:    z.string().describe('Value to type into the field'),
      }),
    }
  )

  const screenshotTool = tool(
    async (): Promise<string> => {
      const { page, error } = await getPage()
      if (error) return error
      try {
        const buf    = await page.screenshot({ type: 'png' })
        const base64 = buf.toString('base64')
        // Return as a data URI the LLM can describe; most multimodal models accept this
        return `data:image/png;base64,${base64.slice(0, 20_000)}... [screenshot taken — ${buf.length} bytes]`
      } catch (err) {
        return `[SCREENSHOT ERROR] ${err instanceof Error ? err.message : String(err)}`
      }
    },
    {
      name: 'take_screenshot',
      description: 'Take a screenshot of the current browser page. Use to visually inspect UI state.',
      schema: z.object({}),
    }
  )

  const closeBrowserTool = tool(
    async (): Promise<string> => {
      if (sharedBrowser) {
        await sharedBrowser.close().catch(() => {})
        sharedBrowser = null
        sharedPage    = null
      }
      return 'Browser closed.'
    },
    {
      name: 'close_browser',
      description: 'Close the browser session. Call when browser testing is complete.',
      schema: z.object({}),
    }
  )

  return [openPageTool, getPageTextTool, clickTool, fillFormTool, screenshotTool, closeBrowserTool]
}
