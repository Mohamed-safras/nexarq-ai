import { Command } from 'commander'
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { Text } from '@opentui/core'
import { printError } from '../output/formatter.ts'
import { loadConfig } from '../config/config-loader.ts'
import { createPageTUI } from '../lib/tui-page.ts'
import { runOrchestrator } from '@nexarq/agent-runtime'

export function explainCommand(): Command {
  return new Command('explain')
    .description('Explain any file or line range in plain English')
    .argument('<target>', 'File path, or file:line, or file:start-end (e.g. src/auth.ts:42-80)')
    .option('-d, --dir <path>', 'Project root directory')
    .action(async (target: string, options: { dir?: string }) => {
      const config = await loadConfig()
      const workingDirectory = options.dir ?? process.cwd()

      const colonIndex = target.lastIndexOf(':')
      let filePath  = target
      let lineRange: string | null = null

      if (colonIndex !== -1 && !target.slice(colonIndex + 1).includes('/')) {
        filePath  = target.slice(0, colonIndex)
        lineRange = target.slice(colonIndex + 1)
      }

      const fullPath = join(workingDirectory, filePath)
      if (!existsSync(fullPath)) {
        printError(`File not found: ${filePath}`)
        process.exit(1)
      }

      const allLines = readFileSync(fullPath, 'utf-8').split('\n')
      let startLine = 1
      let endLine   = Math.min(allLines.length, 300)

      if (lineRange) {
        const parts = lineRange.split('-')
        startLine = Math.max(1, parseInt(parts[0] ?? '1', 10))
        endLine   = parts[1]
          ? Math.min(allLines.length, parseInt(parts[1], 10))
          : Math.min(startLine + 60, allLines.length)
      }

      const codeBlock = allLines.slice(startLine - 1, endLine).join('\n')
      const lineLabel = lineRange ? `:${startLine}-${endLine}` : ''

      const tui = await createPageTUI(`EXPLAIN  ·  ${filePath}${lineLabel}`, 'EXPLANATION')
      const { theme } = tui
      tui.status.content = `  Explaining ${filePath}${lineLabel}...`

      await tui.withError(async () => {
        await runOrchestrator({
          task: `Explain this code from ${filePath}${lineLabel} in plain English.\nDescribe what it does, why it matters, any non-obvious logic, and potential risks.\nBe concise — assume a senior developer audience.\n\n\`\`\`\n${codeBlock}\n\`\`\``,
          triggerSource: 'on-demand',
          workingDirectory,
          runConfig: {
            provider: config.provider,
            ...(config.model ? { model: config.model } : {}),
            mode: 'smart',
            agents: ['explain'],
          },
          onEvent: (event) => {
            if (event.type === 'agent:chunk') {
              tui.body.add(Text({ content: `  ${event.text}`, fg: theme.fg }))
            }
          },
        })

        tui.status.content = '  Press any key to exit.'
        await tui.waitForKey()
        tui.renderer.destroy()
      })
    })
}
