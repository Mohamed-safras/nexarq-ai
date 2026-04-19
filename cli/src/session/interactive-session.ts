import * as readline from 'node:readline'
import { loadConfig } from '../config/config-loader.ts'
import { getThemeByVariant, themeToAnsi } from '../output/tui/theme.ts'

const R    = '\x1b[0m'
const BOLD = '\x1b[1m'
const DIM  = '\x1b[2m'

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
  const tr = parseInt(to.slice(1, 3), 16),   tg = parseInt(to.slice(3, 5), 16),   tb = parseInt(to.slice(5, 7), 16)
  return Array.from({ length: steps }, (_, i) => {
    const t = steps === 1 ? 0 : i / (steps - 1)
    const r = Math.round(fr + (tr - fr) * t)
    const g = Math.round(fg + (tg - fg) * t)
    const b = Math.round(fb + (tb - fb) * t)
    return `\x1b[38;2;${r};${g};${b}m`
  })
}

/**
 * Interactive REPL — the default `nexarq` experience.
 *
 * Every turn routes through runConversationTurn which:
 * - Persists session history (.nexarq/session.json)
 * - Prunes context deterministically when history > 30 entries
 * - Selects the right tool (review, code, explain, search, browser)
 * - Suggests follow-up actions after substantive tasks
 */
export async function runInteractiveSession(): Promise<void> {
  const config = await loadConfig()
  const theme  = getThemeByVariant(config.theme ?? 'dark')
  const c      = themeToAnsi(theme)

  const gradients = lerp(theme.cyan, theme.purple, LOGO.length)
  process.stdout.write('\n')
  for (let i = 0; i < LOGO.length; i++) {
    process.stdout.write((gradients[i] ?? '') + LOGO[i] + R + '\n')
  }
  process.stdout.write('\n')
  process.stdout.write(c.dim + '  parallel AI coding team  ·  v0.1.0' + R + '\n\n')
  process.stdout.write(DIM + '  Chat naturally — review, code, explain, research, or just ask.\n' + R)
  process.stdout.write(DIM + '  Type "help" for commands, "exit" to quit.\n' + R + '\n')

  const { runConversationTurn } = await import('@nexarq/agent-runtime')
  const workingDirectory = process.cwd()
  const runConfig = {
    provider: config.provider as import('@nexarq/common/types').ProviderName,
    ...(config.model ? { model: config.model } : {}),
    unsafeShell: config.unsafeShell ?? false,
  }

  const rl = readline.createInterface({
    input:    process.stdin,
    output:   process.stdout,
    prompt:   c.cyan + BOLD + '  nexarq' + R + c.dim + ' › ' + R,
    terminal: true,
  })

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
      })

      // Clear spinner line
      process.stdout.write('                   \r')

      // Print response
      const responseLines = result.response.trim().split('\n')
      for (const line of responseLines) {
        process.stdout.write('  ' + line + '\n')
      }

      // Print suggested follow-ups
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
    ['<task>',          'Implement, fix, or refactor code using the agent team'],
    ['review / scan',   'Run full 31-agent parallel code review on current diff'],
    ['explain <file>',  'Explain any file or line range in plain English'],
    ['search <query>',  'Web search for docs, CVEs, Stack Overflow answers'],
    ['help',            'Show this help'],
    ['exit / quit',     'Exit the session'],
  ]
  process.stdout.write('\n')
  for (const [cmd, desc] of rows) {
    process.stdout.write('  ' + c.cyan + cmd.padEnd(22) + R + c.dim + desc + R + '\n')
  }
  process.stdout.write(
    '\n' + c.dim + '  You can also just describe tasks naturally — the assistant picks the right tools.\n' + R + '\n'
  )
}
