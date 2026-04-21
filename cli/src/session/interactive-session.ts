import { relative, resolve } from 'node:path'
import * as readline from 'node:readline'
import type { NexarqConfig } from '../config/config-loader.ts'
import { loadConfig } from '../config/config-loader.ts'
import { createEditSession } from '../lib/edit-approval.ts'
import { streamingApproveEdit } from '../lib/streaming-preview.ts'
import { getThemeByVariant, themeToAnsi } from '../output/tui/theme.ts'

const R = '\x1b[0m'
const BOLD = '\x1b[1m'

const LOGO = [
  '  ██╗  ██╗███████╗██╗  ██╗ █████╗ ██████╗  ██████╗',
  '  ████╗ ██║██╔════╝╚██╗██╔╝██╔══██╗██╔══██╗██╔═══██╗',
  '  ██╔██╗██║█████╗   ╚███╔╝ ███████║██████╔╝██║   ██║',
  '  ██║╚██╗██║██╔══╝   ██╔██╗██╔══██║██╔══██╗██║▄▄ ██║',
  '  ██║ ╚████║███████╗██╔╝ ██╗██║  ██║██║  ██║╚██████╔╝',
  '  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚══▀▀═╝',
]

function lerp(from: string, to: string, steps: number): string[] {
  const fr = parseInt(from.slice(1, 3), 16), fg = parseInt(from.slice(3, 5), 16), fb = parseInt(from.slice(5, 7), 16)
  const tr = parseInt(to.slice(1, 3), 16), tg = parseInt(to.slice(3, 5), 16), tb = parseInt(to.slice(5, 7), 16)
  return Array.from({ length: steps }, (_, i) => {
    const t = steps === 1 ? 0 : i / (steps - 1)
    return `\x1b[38;2;${Math.round(fr + (tr - fr) * t)};${Math.round(fg + (tg - fg) * t)};${Math.round(fb + (tb - fb) * t)}m`
  })
}

function stripAnsi(s: string): string {
  return s.replace(/\x1b\[[0-9;]*[mGKHF]/g, '')
}

function pad(s: string, width: number): string {
  const vis = stripAnsi(s).length
  if (vis > width) {
    // Truncate to fit, preserving ANSI escape sequences
    let count = 0
    let result = ''
    let inEscape = false
    for (const ch of s) {
      if (ch === '\x1b') { inEscape = true; result += ch; continue }
      if (inEscape) { result += ch; if (/[mGKHF]/.test(ch)) inEscape = false; continue }
      if (count >= width - 1) { result += '\x1b[0m…'; break }
      result += ch; count++
    }
    return result
  }
  return s + ' '.repeat(Math.max(0, width - vis))
}

function renderWelcomeBox(c: ReturnType<typeof themeToAnsi>, theme: ReturnType<typeof getThemeByVariant>, config: NexarqConfig): void {
  const cols = Math.max(process.stdout.columns || 80, 60)
  const boxW = cols - 2
  const inner = boxW - 2
  const MIN_RIGHT = 34
  const leftW = Math.min(Math.max(52, Math.floor(inner * 0.52)), inner - MIN_RIGHT - 1)
  const rightW = inner - leftW - 1   // -1 for │ divider

  const titleStr = `─── Nexarq v0.1.0 `
  const top = `╭${titleStr}${'─'.repeat(Math.max(0, boxW - 2 - titleStr.length))}╮`
  const bot = `╰${'─'.repeat(boxW - 2)}╯`

  const username = process.env['USERNAME'] || process.env['USER'] || 'developer'
  const cwd = process.cwd()
  const provider = config.provider + (config.model ? ` · ${config.model}` : '')
  const gradients = lerp(theme.cyan, theme.purple, LOGO.length)

  const L: string[] = [
    '',
    `  ${BOLD}Welcome back, ${username}!${R}`,
    '',
    ...LOGO.map((line, i) => `${gradients[i] ?? ''}${line}${R}`),
    '',
    `  ${c.dim}${provider}${R}`,
    `  ${c.dim}${cwd}${R}`,
    '',
  ]

  const sep = `─`.repeat(rightW - 1)
  const cmdLine = (name: string, desc: string) =>
    ` ${c.cyan}${name.padEnd(10)}${R}${c.dim}${desc}${R}`

  const RL: string[] = [
    '',
    ` ${BOLD}Quick start${R}`,
    ` ${c.dim}${sep}${R}`,
    ' Type any task naturally to get started',
    '',
    ` ${BOLD}Commands${R}`,
    cmdLine('review', 'run 31-agent code review'),
    cmdLine('code', 'implement a feature'),
    cmdLine('explain', 'explain any file'),
    cmdLine('search', 'web search'),
    cmdLine('help', 'show all commands'),
    '',
    ` ${c.dim}exit · quit to leave${R}`,
  ]

  const rows = Math.max(L.length, RL.length)

  process.stdout.write('\n')
  process.stdout.write(c.dim + top + R + '\n')
  for (let i = 0; i < rows; i++) {
    const lc = pad(L[i] ?? '', leftW)
    const rc = pad(RL[i] ?? '', rightW)
    process.stdout.write(c.dim + '│' + R + lc + c.dim + '│' + R + rc + c.dim + '│' + R + '\n')
  }
  process.stdout.write(c.dim + bot + R + '\n\n')
}

export async function runInteractiveSession(): Promise<void> {
  const config = await loadConfig()
  const theme = getThemeByVariant(config.theme ?? 'dark')
  const c = themeToAnsi(theme)

  renderWelcomeBox(c, theme, config)

  const { runConversationTurn } = await import('@nexarq/agent-runtime')
  const workingDirectory = process.cwd()
  const runConfig = {
    provider: config.provider as import('@nexarq/common/types').ProviderName,
    ...(config.model ? { model: config.model } : {}),
    unsafeShell: config.unsafeShell ?? false,
  }
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: c.cyan + BOLD + '  nexarq' + R + c.dim + ' › ' + R,
    terminal: true,
  })

  const editSession = createEditSession()
  const onBeforeWrite = async (filePath: string, oldContent: string | null, newContent: string, line?: number): Promise<boolean> => {
    const fullPath = resolve(workingDirectory, filePath)
    const displayPath = relative(workingDirectory, fullPath).replace(/\\/g, '/')
    rl.pause()
    process.stdout.write('\n')
    const decision = await streamingApproveEdit({ displayPath, fullPath, oldContent: oldContent ?? '', newContent, session: editSession, workingDirectory })
    rl.resume()
    return decision === 'yes'
  }

  rl.prompt()

  rl.on('line', async (raw: string) => {
    const input = raw.trim()

    if (!input) {
      rl.prompt()
      return
    }

    if (input === 'exit' || input === 'quit' || input === 'bye' || input === 'q') {
      process.stdout.write(c.dim + '\n  Goodbye.\n\n' + R)
      rl.close()
      process.exit(0)
    }

    if (input === 'help') {
      printHelp(c)
      rl.prompt()
      return
    }

    rl.pause()
    process.stdout.write('\n' + c.dim + '  ⟳ thinking...\r' + R)

    try {
      const result = await runConversationTurn({
        userMessage: input,
        workingDirectory,
        runConfig,
        onBeforeWrite,
      })

      process.stdout.write('                   \r')

      const responseLines = result.response.trim().split('\n')
      for (const line of responseLines) {
        process.stdout.write('  ' + line + '\n')
      }

      if (result.suggestedFollowups.length > 0) {
        process.stdout.write('\n' + c.dim + '  Next steps:\n' + R)
        result.suggestedFollowups.slice(0, 3).forEach((suggestion, index) => {
          process.stdout.write(c.dim + `  ${index + 1}. ${suggestion}\n` + R)
        })
      }
    } catch (err) {
      process.stdout.write('                   \r')
      process.stdout.write(c.red + `  Error: ${err instanceof Error ? err.message : String(err)}` + R + '\n')
    }

    process.stdout.write('\n')
    rl.resume()
    rl.prompt()
  })

  rl.on('close', () => process.exit(0))
}

function printHelp(c: ReturnType<typeof themeToAnsi>): void {
  const rows: [string, string][] = [
    ['<task>', 'Implement, fix, or refactor code using the agent team'],
    ['review / scan', 'Run full 31-agent parallel code review on current diff'],
    ['explain <file>', 'Explain any file or line range in plain English'],
    ['search <query>', 'Web search for docs, CVEs, Stack Overflow answers'],
    ['help', 'Show this help'],
    ['exit / quit', 'Exit the session'],
  ]
  process.stdout.write('\n')
  for (const [cmd, desc] of rows) {
    process.stdout.write('  ' + c.cyan + cmd.padEnd(22) + R + c.dim + desc + R + '\n')
  }
  process.stdout.write(
    '\n' + c.dim + '  You can also just describe tasks naturally — the assistant picks the right tools.\n' + R + '\n'
  )
}
