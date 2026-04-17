import { Command } from 'commander'
import { watch } from 'node:fs'
import { execSync } from 'node:child_process'
import { Text } from '@opentui/core'
import { THEME } from '../output/tui/theme.ts'
import { loadConfig } from '../config/config-loader.ts'
import { createPageTUI } from '../lib/tui-page.ts'
import { makeDiffResult } from '../lib/make-diff-result.ts'
import { runOrchestrator } from '@nexarq/agent-runtime'

/**
 * nexarq watch
 *
 * Watches for file saves and runs a fast tier-1 review on the diff
 * as you code — findings appear before you commit.
 *
 * Token budget: fast mode only (haiku/flash/minimax) — typically <$0.001/save.
 * Debounces at 2s so rapid saves don't spam the LLM.
 */
export function watchCommand(): Command {
  return new Command('watch')
    .description('Review code changes live as you save files')
    .option('-d, --dir <path>', 'Directory to watch (default: current directory)')
    .action(async (options: { dir?: string }) => {
      const config = await loadConfig()
      const watchDir = options.dir ?? process.cwd()

      const tui = await createPageTUI('WATCH', 'FINDINGS', { exitOnCtrlC: false })
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

          // Clear previous findings
          tui.clearBody()
          tui.body.add(Text({ content: '  Running agents...', fg: THEME.fgDim }))

          const result = await runOrchestrator({
            task: 'Review the following diff',
            diffResult: makeDiffResult(rawDiff),
            triggerSource: 'on-demand',
            runConfig: {
              provider: config.provider,
              ...(config.model ? { model: config.model } : {}),
              mode: 'fast', // always fast in watch mode — costs near zero
            },
          })

          // Repaint findings
          tui.clearBody()

          if (result.summary.totalFindings === 0) {
            tui.body.add(Text({ content: '  No issues found.', fg: THEME.green }))
          } else {
            for (const agentResult of result.results) {
              for (const finding of agentResult.findings) {
                const color = THEME.severity[finding.severity as keyof typeof THEME.severity] ?? THEME.fg
                tui.body.add(Text({
                  content: `  [${finding.severity?.toUpperCase() ?? 'INFO'}] ${finding.message}`,
                  fg: color,
                }))
                if (finding.file) {
                  tui.body.add(Text({
                    content: `    ${finding.file}${finding.line ? `:${finding.line}` : ''}`,
                    fg: THEME.fgDim,
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

      // Run once on startup
      void runReview()

      // Ctrl+C exits
      tui.renderer.keyInput.on('keypress', (event) => {
        if (event.ctrl && event.name === 'c') {
          watcher.close()
          tui.renderer.destroy()
          process.exit(0)
        }
      })
    })
}
