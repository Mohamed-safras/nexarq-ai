import { Command } from 'commander'
import { execSync, execFileSync } from 'node:child_process'
import { Text } from '@opentui/core'
import { THEME } from '../output/tui/theme.ts'
import { printError } from '../output/formatter.ts'
import { loadConfig } from '../config/config-loader.ts'
import { createPageTUI } from '../lib/tui-page.ts'
import { runOrchestrator } from '@nexarq/agent-runtime'

/**
 * nexarq commit
 *
 * LLM-generated git commit message from the staged diff.
 * Token budget: ~1k input tokens max (cheap even on paid models).
 * Uses the cheapest available model — no deep analysis needed.
 */
export function commitCommand(): Command {
  return new Command('commit')
    .description('Generate a commit message with AI and commit staged changes')
    .option('-n, --no-verify', 'Skip git hooks')
    .option('-d, --dry-run',   'Show the generated message without committing')
    .option('-e, --edit',      'Open the message in $EDITOR before committing')
    .action(async (options: { noVerify?: boolean; dryRun?: boolean; edit?: boolean }) => {
      const config = await loadConfig()

      // Get staged diff — token budget: 4k chars (~1k tokens)
      let diff: string
      try {
        diff = execSync('git diff --cached', { encoding: 'utf-8' }).trim()
      } catch {
        printError('Not a git repository or git not found.')
        process.exit(1)
      }

      if (!diff) {
        printError('No staged changes. Run `git add` first.')
        process.exit(1)
      }

      // Truncate to ~1k tokens to keep cost near zero
      const truncated = diff.length > 4000 ? diff.slice(0, 4000) + '\n... [truncated]' : diff

      const tui = await createPageTUI('COMMIT', 'MESSAGE')
      tui.status.content = '  Generating commit message...'

      await tui.withError(async () => {
        let generatedMessage = ''

        const result = await runOrchestrator({
          task: `Write a concise git commit message for this staged diff.

Rules:
- First line: imperative mood, max 72 chars (e.g. "Add input validation to createUser endpoint")
- If needed, a blank line then bullet points for details
- No "This commit..." preamble
- Output ONLY the commit message text, nothing else

Diff:
${truncated}`,
          triggerSource: 'sdk',
          runConfig: {
            provider: config.provider,
            ...(config.model ? { model: config.model } : {}),
            mode: 'fast',
            agents: ['summary'],
          },
          onEvent: (event) => {
            if (event.type === 'agent:chunk') {
              generatedMessage += event.text
              tui.body.add(Text({ content: `  ${event.text}`, fg: THEME.fg }))
            }
          },
        })

        generatedMessage = result.finalOutput.trim() || generatedMessage.trim()

        if (options.dryRun) {
          tui.status.content = '  Dry run — not committed. Press any key to exit.'
          await tui.waitForKey()
          tui.renderer.destroy()
          return
        }

        tui.status.content = '  Press Enter to commit, Esc to cancel.'
        const confirmed = await tui.waitForConfirm()
        tui.renderer.destroy()

        if (!confirmed) {
          console.log('Commit cancelled.')
          return
        }

        try {
          const args = ['commit', '-m', generatedMessage]
          if (options.noVerify) args.push('--no-verify')
          execFileSync('git', args, { stdio: 'inherit' })
        } catch {
          printError('git commit failed.')
          process.exit(1)
        }
      })
    })
}
