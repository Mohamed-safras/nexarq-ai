import { createCliRenderer, Box, Text, ScrollBox } from '@opentui/core'
import type { CliRenderer, StyledText } from '@opentui/core'
import { THEME } from '../output/tui/theme.ts'

export interface PageTUI {
  renderer: CliRenderer
  /** ScrollBox node — append Text children here */
  body: { add(child: unknown): void }
  /** Remove all children from the body scroll area */
  clearBody(): void
  /** Footer status line — assign .content to update */
  status: { content: StyledText | string }
  /** Wait for any keypress */
  waitForKey(): Promise<void>
  /** Wait for Enter (true) or Esc / Ctrl+C (false) */
  waitForConfirm(): Promise<boolean>
  /**
   * Run an async operation; on throw: destroy renderer, print error, exit(1).
   * Returns the resolved value on success.
   */
  withError<T>(fn: () => Promise<T>): Promise<T>
}

/**
 * Creates a standard 3-panel full-screen TUI layout:
 *
 *   ┌─ header (bgAlt) ──────────────────────────────────────┐
 *   │  NEXARQ <TITLE>                                        │
 *   ├─ body panel (bordered, flex-grow) ────────────────────┤
 *   │  <scrollable content area>                            │
 *   ├─ footer (bgAlt) ──────────────────────────────────────┤
 *   │  <status text>                                        │
 *   └────────────────────────────────────────────────────────┘
 */
export async function createPageTUI(
  title: string,
  bodyTitle = '',
  opts: { exitOnCtrlC?: boolean } = {},
): Promise<PageTUI> {
  const renderer = await createCliRenderer({ exitOnCtrlC: opts.exitOnCtrlC ?? false })

  const body = ScrollBox({ width: '100%', flexGrow: 1, flexDirection: 'column' })
  const status = Text({ content: '', fg: THEME.fgDim })

  renderer.root.add(
    Box(
      { width: '100%', height: '100%', flexDirection: 'column', backgroundColor: THEME.bg },
      Box(
        { width: '100%', backgroundColor: THEME.bgAlt },
        Text({ content: `  NEXARQ ${title}`, fg: THEME.cyan }),
      ),
      Box(
        { flexGrow: 1, border: true, borderColor: THEME.fgDim, title: bodyTitle ? ` ${bodyTitle} ` : '' },
        body,
      ),
      Box({ width: '100%', backgroundColor: THEME.bgAlt }, status),
    ),
  )

  function waitForKey(): Promise<void> {
    return new Promise<void>((resolve) => {
      renderer.keyInput.on('keypress', () => resolve())
    })
  }

  function waitForConfirm(): Promise<boolean> {
    return new Promise<boolean>((resolve) => {
      renderer.keyInput.on('keypress', (event) => {
        if (event.name === 'return') resolve(true)
        if (event.name === 'escape' || (event.ctrl && event.name === 'c')) resolve(false)
      })
    })
  }

  async function withError<T>(fn: () => Promise<T>): Promise<T> {
    try {
      return await fn()
    } catch (err) {
      renderer.destroy()
      const { printError } = await import('../output/formatter.ts')
      printError(err instanceof Error ? err.message : String(err))
      process.exit(1)
    }
  }

  function clearBody(): void {
    const node = body as unknown as { getChildren(): { id: string }[]; remove(id: string): void }
    for (const child of node.getChildren()) {
      node.remove(child.id)
    }
  }

  return { renderer, body, status, waitForKey, waitForConfirm, withError, clearBody }
}
