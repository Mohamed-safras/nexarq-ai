import { Command } from 'commander'
import { runOrchestrator } from '@nexarq/agent-runtime'
import { Text } from '@opentui/core'
import { THEME } from '../output/tui/theme.ts'
import { loadConfig } from '../config/config-loader.ts'
import { createPageTUI } from '../lib/tui-page.ts'

export function codeCommand(): Command {
  const command = new Command('code')
    .description('Run the autonomous coding agent on a task')
    .argument('<task>', 'The task to perform, e.g. "fix the auth bug in src/auth.ts"')
    .option('-d, --dir <path>', 'Project directory (default: current directory)')

  command.action(async (task: string, options: { dir?: string }) => {
    const config = await loadConfig()
    const workingDirectory = options.dir ?? process.cwd()

    const tui = await createPageTUI(`CODER  ·  ${task}`, 'OUTPUT')
    tui.status.content = '  Thinking...'

    let chunkBuffer = ''

    function flushBuffer(): void {
      if (!chunkBuffer.trim()) return
      for (const line of chunkBuffer.split('\n')) {
        tui.body.add(Text({ content: `  ${line}`, fg: THEME.fg }))
      }
      chunkBuffer = ''
    }

    try {
      const result = await runOrchestrator({
        task,
        triggerSource: 'coding-agent',
        workingDirectory,
        runConfig: {
          provider: config.provider,
          ...(config.model ? { model: config.model } : {}),
        },
        onEvent: (event) => {
          if (event.type === 'agent:chunk') {
            chunkBuffer += event.text
            if (chunkBuffer.includes('\n')) flushBuffer()
          }
        },
      })

      flushBuffer()
      tui.status.content = '  Done  ·  press any key to exit'

      if (result.finalOutput) {
        tui.body.add(Text({ content: '', fg: THEME.fg }))
        tui.body.add(Text({ content: `  ${result.finalOutput}`, fg: THEME.green }))
      }

      await tui.waitForKey()
      tui.renderer.destroy()
    } catch (codeError) {
      flushBuffer()
      tui.body.add(Text({
        content: `  Error: ${codeError instanceof Error ? codeError.message : String(codeError)}`,
        fg: THEME.red,
      }))
      tui.status.content = '  Failed  ·  press any key to exit'

      await tui.waitForKey()
      tui.renderer.destroy()

      const { printError } = await import('../output/formatter.ts')
      printError(codeError instanceof Error ? codeError.message : String(codeError))
      process.exit(1)
    }
  })

  return command
}
