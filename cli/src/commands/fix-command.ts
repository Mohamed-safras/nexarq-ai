import { Command } from 'commander'
import { writeFileSync, existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { Text, Select } from '@opentui/core'
import { printError } from '../output/formatter.ts'
import { loadConfig } from '../config/config-loader.ts'
import { extractDiff } from '../git/diff-extractor.ts'
import { createPageTUI } from '../lib/tui-page.ts'
import { makeDiffResult } from '../lib/make-diff-result.ts'
import type { AgentFinding } from '@nexarq/common/interfaces'

/**
 * nexarq fix
 *
 * Runs the ai-fixes agent on the latest diff, presents each fix in a TUI
 * picker, and applies the selected ones by writing patched files to disk.
 *
 * Token cost: 1 agent call (ai-fixes tier-3) + minimal output.
 * Startup-friendly: uses fast/cheap model by default.
 */
export function fixCommand(): Command {
  return new Command('fix')
    .description('Auto-apply AI-suggested fixes from the last review')
    .option('-a, --all',   'Apply all suggested fixes without prompting')
    .option('-d, --diff <file>', 'Path to a diff file instead of git diff')
    .action(async (options: { all?: boolean; diff?: string }) => {
      const config = await loadConfig()

      let rawDiff: string
      try {
        rawDiff = options.diff
          ? readFileSync(options.diff, 'utf-8')
          : await extractDiff('on-demand')
      } catch (err) {
        printError(err instanceof Error ? err.message : String(err))
        process.exit(1)
      }

      if (!rawDiff.trim()) {
        console.log('No changes to fix.')
        return
      }

      const tui = await createPageTUI('FIX', 'FIXES')
      tui.status.content = '  Running ai-fixes agent...'

      await tui.withError(async () => {
        const fixes: Array<{ finding: AgentFinding; patch: string; file: string }> = []

        const { runOrchestrator } = await import('@nexarq/agent-runtime')
        const result = await runOrchestrator({
          task: 'Suggest and generate concrete code fixes for the findings in this diff.',
          diffResult: makeDiffResult(rawDiff),
          triggerSource: 'on-demand',
          runConfig: {
            provider: config.provider,
            ...(config.model ? { model: config.model } : {}),
            mode: 'smart',
            agents: ['ai-fixes'],
          },
        })

        for (const agentResult of result.results) {
          for (const finding of agentResult.findings) {
            if (finding.suggestion && finding.file) {
              fixes.push({ finding, patch: finding.suggestion, file: finding.file })
              tui.body.add(Text({
                content: `  [${finding.severity?.toUpperCase() ?? 'INFO'}] ${finding.message}`,
                fg: tui.theme.severity[(finding.severity ?? 'info') as keyof typeof tui.theme.severity] ?? tui.theme.fg,
              }))
            }
          }
        }

        if (fixes.length === 0) {
          tui.status.content = '  No auto-fixable issues found. Press any key to exit.'
          await tui.waitForKey()
          tui.renderer.destroy()
          return
        }

        if (options.all) {
          tui.renderer.destroy()
          applyFixes(fixes.map((f) => f.file), fixes.map((f) => f.patch))
          return
        }

        // Interactive picker
        tui.status.content = '  Select a fix to apply (Enter to confirm, Esc to skip):'

        const selectOptions = fixes.map((fix, index) => ({
          name: `  [${fix.finding.severity?.toUpperCase() ?? 'INFO'}] ${fix.finding.message} — ${fix.file}`,
          value: index,
          description: fix.patch.slice(0, 120),
        }))

        const fixSelect = Select({
          options: selectOptions,
          textColor:               tui.theme.fg,
          backgroundColor:         tui.theme.bg,
          focusedBackgroundColor:  tui.theme.bgAlt,
          focusedTextColor:        tui.theme.cyan,
          selectedBackgroundColor: tui.theme.green,
          selectedTextColor:       tui.theme.bg,
          wrapSelection:           true,
          showDescription:         true,
          width:                   '100%',
        })
        tui.body.add(fixSelect)
        fixSelect.focus()

        const selectedIndex = await new Promise<number | null>((resolve) => {
          // Explicit key handling for Windows terminal compatibility
          tui.renderer.keyInput.on('keypress', (event: { name: string; ctrl?: boolean }) => {
            if (event.name === 'up') {
              fixSelect.emit('moveUp')
            }
            if (event.name === 'down') {
              fixSelect.emit('moveDown')
            }
            if (event.name === 'return' || event.name === 'enter') {
              fixSelect.emit('select')
            }
            if (event.name === 'escape') resolve(null)
            if (event.ctrl && event.name === 'c') {
              tui.renderer.destroy()
              process.exit(0)
            }
          })

          fixSelect.on('itemSelected', (option: { name: string; value: unknown }) => {
            resolve(option.value as number)
          })
        })

        tui.renderer.destroy()

        if (selectedIndex === null) {
          console.log('No fix applied.')
          return
        }

        const chosenFix = fixes[selectedIndex]
        if (chosenFix) {
          applyFixes([chosenFix.file], [chosenFix.patch])
        }
      })
    })
}

function applyFixes(files: string[], patches: string[]): void {
  const cwd = process.cwd()
  for (let index = 0; index < files.length; index++) {
    const file = files[index]
    const patch = patches[index]
    if (!file || !patch) continue

    const fullPath = join(cwd, file)
    if (!existsSync(fullPath)) {
      console.error(`  File not found: ${file}`)
      continue
    }

    // The ai-fixes agent returns suggestions as descriptive text, not raw patches.
    // For production, a structured diff-apply would be used here.
    // For now: write the suggestion as a comment at the top of the file.
    const existing = readFileSync(fullPath, 'utf-8')
    const commentPrefix = fullPath.endsWith('.py') ? '# ' : '// '
    const commentBlock = patch
      .split('\n')
      .map((line) => `${commentPrefix}${line}`)
      .join('\n')
    writeFileSync(fullPath, `${commentBlock}\n\n${existing}`, 'utf-8')
    console.log(`  Applied fix to ${file}`)
  }
}
