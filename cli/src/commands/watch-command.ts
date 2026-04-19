import { Command } from 'commander'
import { watch } from 'node:fs'
import { execSync } from 'node:child_process'
import { Text } from '@opentui/core'
import { loadConfig } from '../config/config-loader.ts'
import { createPageTUI } from '../lib/tui-page.ts'
import { makeDiffResult } from '../lib/make-diff-result.ts'
import { runOrchestrator } from '@nexarq/agent-runtime'

export function watchCommand(): Command {
  return new Command('watch')
    .description('Review code changes live as you save files')
    .option('-d, --dir <path>', 'Directory to watch (default: current directory)')
    .action(async (options: { dir?: string }) => {
      const config   = await loadConfig()
      const watchDir = options.dir ?? process.cwd()

      const tui = await createPageTUI('WATCH', 'FINDINGS', { exitOnCtrlC: false })
      const { theme } = tui
      tui.status.content = `  Watching ${watchDir}  ·  Ctrl+C to stop`

      let debounceTimer: ReturnType<typeof setTimeout> | null = null
      let isReviewing = false

      async function runReview(): Promise<void> {
        if (isReviewing) return
        isReviewing = true
        tui.status.content = '  Reviewing...'

        try {
          const rawDiff = execSync('git diff', { encoding: 'utf-8', cwd: watchDir }).trim()

          if (!rawDiff) {
            tui.status.content = '  No unstaged changes — watching...'
            isReviewing = false
            return
          }

          tui.clearBody()
          tui.body.add(Text({ content: '  Running agents...', fg: theme.fgDim }))

          const result = await runOrchestrator({
            task: 'Review the following diff',
            diffResult: makeDiffResult(rawDiff),
            triggerSource: 'on-demand',
            runConfig: {
              provider: config.provider,
              ...(config.model ? { model: config.model } : {}),
              mode: 'fast',
            },
          })

          tui.clearBody()

          if (result.summary.totalFindings === 0) {
            tui.body.add(Text({ content: '  No issues found.', fg: theme.green }))
          } else {
            for (const agentResult of result.results) {
              for (const finding of agentResult.findings) {
                const color = theme.severity[finding.severity as keyof typeof theme.severity] ?? theme.fg
                tui.body.add(Text({
                  content: `  [${finding.severity?.toUpperCase() ?? 'INFO'}] ${finding.message}`,
                  fg: color,
                }))
                if (finding.file) {
                  tui.body.add(Text({
                    content: `    ${finding.file}${finding.line ? `:${finding.line}` : ''}`,
                    fg: theme.fgDim,
                  }))
                }
              }
            }
          }

          const { critical, high, medium, low } = result.summary
          tui.status.content = `  Last review: ${critical}c ${high}h ${medium}m ${low}l  ·  watching...`
        } catch {
          tui.status.content = '  Review failed — watching...'
        } finally {
          isReviewing = false
        }
      }

      const watcher = watch(watchDir, { recursive: true }, (_, filename) => {
        if (!filename) return
        if (filename.includes('node_modules') || filename.includes('.git')) return
        if (!filename.match(/\.(ts|tsx|js|jsx|py|go|rs|java|cs|rb|php|css|html|json|yaml|yml|sql)$/)) return

        if (debounceTimer) clearTimeout(debounceTimer)
        debounceTimer = setTimeout(() => void runReview(), 2000)
      })

      void runReview()

      tui.renderer.keyInput.on('keypress', (event) => {
        if (event.ctrl && event.name === 'c') {
          watcher.close()
          tui.renderer.destroy()
          process.exit(0)
        }
      })
    })
}
