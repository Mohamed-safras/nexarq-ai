import { createCliRenderer, Box, Text, ScrollBox } from '@opentui/core'
import { THEME, type SeverityKey } from './theme.ts'
import type { RunSummary } from '@nexarq/common/interfaces'

type AgentStatus = 'pending' | 'running' | 'done' | 'error'

interface AgentRow {
  text: ReturnType<typeof Text>
  status: AgentStatus
  index: number
}

export interface RunTUI {
  initAgents(names: string[]): void
  setAgentStatus(name: string, status: AgentStatus): void
  addFinding(agentName: string, severity: string, lines: string[]): void
  updateFooter(agentsRun: number, total: number, summary: Partial<RunSummary>, tokens: number): void
  showComplete(durationMs: number): void
  waitForExit(): Promise<void>
  destroy(): void
}

const AGENT_ICON: Record<AgentStatus, string> = {
  pending: ' · ',
  running: ' ● ',
  done:    ' ✓ ',
  error:   ' ✗ ',
}

const AGENT_COLOR: Record<AgentStatus, string> = {
  pending: THEME.fgDim,
  running: THEME.cyan,
  done:    THEME.green,
  error:   THEME.red,
}

function severityColor(severity: string): string {
  return THEME.severity[severity as SeverityKey] ?? THEME.fgDim
}

export async function createRunTUI(diffLineCount: number): Promise<RunTUI> {
  const renderer = await createCliRenderer()

  // ── Header ────────────────────────────────────────────────────────────────
  const headerText = Text({
    content: `  NEXARQ  ·  reviewing ${diffLineCount} diff lines`,
    fg: THEME.cyan,
  })

  const headerBox = Box(
    { width: '100%', backgroundColor: THEME.bgAlt, paddingTop: 0, paddingBottom: 0 },
    headerText,
  )

  // ── Agents panel ──────────────────────────────────────────────────────────
  const agentsScrollBox = ScrollBox({
    width: '100%',
    height: '100%',
    flexDirection: 'column',
  })

  const agentsPanel = Box(
    {
      width: 28,
      flexDirection: 'column',
      backgroundColor: THEME.bgPanel,
      border: true,
      borderColor: THEME.fgDim,
      title: ' AGENTS ',
      titleAlignment: 'left',
    },
    agentsScrollBox,
  )

  // ── Findings panel ────────────────────────────────────────────────────────
  const findingsScrollBox = ScrollBox({
    width: '100%',
    height: '100%',
    flexDirection: 'column',
  })

  const findingsPanel = Box(
    {
      flexGrow: 1,
      flexDirection: 'column',
      backgroundColor: THEME.bg,
      border: true,
      borderColor: THEME.fgDim,
      title: ' FINDINGS ',
      titleAlignment: 'left',
    },
    findingsScrollBox,
  )

  // ── Body ──────────────────────────────────────────────────────────────────
  const bodyBox = Box(
    { width: '100%', flexGrow: 1, flexDirection: 'row' },
    agentsPanel,
    findingsPanel,
  )

  // ── Footer ────────────────────────────────────────────────────────────────
  const footerText = Text({
    content: '  Waiting for agents...',
    fg: THEME.fgDim,
  })

  const footerBox = Box(
    { width: '100%', backgroundColor: THEME.bgAlt, paddingTop: 0, paddingBottom: 0 },
    footerText,
  )

  // ── Root layout ───────────────────────────────────────────────────────────
  const root = Box(
    { width: '100%', height: '100%', flexDirection: 'column', backgroundColor: THEME.bg },
    headerBox,
    bodyBox,
    footerBox,
  )

  renderer.root.add(root)

  const agentRows = new Map<string, AgentRow>()
  let exitResolve: (() => void) | null = null

  // ── q / Enter to exit after run completes ─────────────────────────────────
  let runComplete = false
  renderer.keyInput.on('keypress', (event: { name: string; ctrl?: boolean }) => {
    if (!runComplete) return
    if (event.name === 'q' || event.name === 'return' || event.ctrl) {
      exitResolve?.()
    }
  })

  return {
    initAgents(names: string[]) {
      names.forEach((name, index) => {
        const rowText = Text({ content: `${AGENT_ICON.pending}${name}`, fg: AGENT_COLOR.pending })
        agentsScrollBox.add(rowText)
        agentRows.set(name, { text: rowText, status: 'pending', index })
      })
    },

    setAgentStatus(name: string, status: AgentStatus) {
      const row = agentRows.get(name)
      if (!row) return

      const icon = AGENT_ICON[status]
      const fg   = AGENT_COLOR[status]

      // Swap the Text node to change color — use stored index to avoid getChildren
      const newText = Text({ content: `${icon}${name}`, fg })
      agentsScrollBox.add(newText, row.index)
      agentsScrollBox.remove(row.text.id)

      row.text   = newText
      row.status = status
    },

    addFinding(agentName: string, severity: string, lines: string[]) {
      const color    = severityColor(severity)
      const label    = severity.toUpperCase().padEnd(8)
      const titleRow = Text({ content: `  [${label}] ${agentName}`, fg: color })
      findingsScrollBox.add(titleRow)

      for (const line of lines) {
        const lineRow = Text({ content: `    ${line}`, fg: THEME.fgDim })
        findingsScrollBox.add(lineRow)
      }

      const spacer = Text({ content: '', fg: THEME.fgDim })
      findingsScrollBox.add(spacer)
    },

    updateFooter(agentsRun: number, total: number, summary: Partial<RunSummary>, tokens: number) {
      const parts: string[] = [`  ${agentsRun}/${total} agents`]

      if (summary.critical) parts.push(`${summary.critical} critical`)
      if (summary.high)     parts.push(`${summary.high} high`)
      if (summary.medium)   parts.push(`${summary.medium} medium`)
      if (summary.low)      parts.push(`${summary.low} low`)
      if (summary.info)     parts.push(`${summary.info} info`)
      if (tokens > 0)       parts.push(`${tokens.toLocaleString()} tokens`)

      ;(footerText as unknown as { content: string }).content = parts.join('  ·  ')
    },

    showComplete(durationMs: number) {
      runComplete = true
      const elapsed = (durationMs / 1000).toFixed(1)

      const doneText = Text({
        content: `  Review complete in ${elapsed}s  ·  press q or Enter to exit`,
        fg: THEME.green,
      })
      footerBox.add(doneText)
    },

    waitForExit(): Promise<void> {
      if (!runComplete) return Promise.resolve()
      return new Promise((resolve) => {
        exitResolve = resolve
      })
    },

    destroy() {
      renderer.destroy()
    },
  }
}
