import { select } from '@inquirer/prompts'
import { runWorkflowOrchestrator } from '@nexarq/agent-runtime'
import chalk from 'chalk'
import { Command } from 'commander'
import { resolve, relative } from 'node:path'
import { loadConfig } from '../config/config-loader.ts'
import { createEditSession } from '../lib/edit-approval.ts'
import { streamingApproveEdit } from '../lib/streaming-preview.ts'
import { printError } from '../output/formatter.ts'
import { createRunTUI } from '../output/tui/run-tui.ts'
import { createTuiEventHandler } from '../output/tui/tui-event-handler.ts'

export function codeCommand(): Command {
  const command = new Command('code')
    .description('Run a parallel multi-agent coding team on a task')
    .argument('<task>', 'The coding task, e.g. "add rate limiting to the API"')
    .option('-d, --dir <path>', 'Project directory (default: current directory)')

  command.action(async (task: string, options: { dir?: string }) => {
    const config = await loadConfig()
    const workingDirectory = options.dir ?? process.cwd()

    const tui = await createRunTUI(0)
    const { state: tuiState, onEvent } = createTuiEventHandler(tui)
    const editSession = createEditSession()
    let tuiAlive = true

    try {
      const result = await runWorkflowOrchestrator({
        task,
        workingDirectory,
        runConfig: {
          provider: config.provider,
          ...(config.model ? { model: config.model } : {}),
        },
        onEvent,
        onBeforeWrite: async (filePath, oldContent, newContent, line) => {
          if (tuiAlive) { tui.destroy(); tuiAlive = false }
          const fullPath    = resolve(workingDirectory, filePath)
          const displayPath = relative(workingDirectory, fullPath).replace(/\\/g, '/')
          const decision = await streamingApproveEdit({
            displayPath,
            fullPath,
            oldContent: oldContent ?? '',
            newContent,
            session: editSession,
            workingDirectory,
          })
          return decision === 'yes'
        },
      })

      if (tuiAlive) {
        tui.updateFooter(tuiState.totalAgents, tuiState.totalAgents, {}, 0)
        tui.showComplete(result.durationMs)
        await tui.waitForExit()
        tui.destroy()
        tuiAlive = false
      }

      printWorkflowReport(result)

      if (result.modifiedFiles.length > 0) {
        console.log()
        console.log(
          chalk.gray('  ──  ') +
          chalk.bold('What next?') +
          chalk.gray(`  ${result.modifiedFiles.length} file(s) modified`)
        )
        console.log()

        const choice = await select({
          message: 'Choose an action',
          choices: [
            { name: chalk.cyan('⟳') + '  review   run code review on the changes', value: 'review', short: 'review' },
            { name: chalk.green('✓') + '  commit   commit the changes with a message', value: 'commit', short: 'commit' },
            { name: chalk.gray('·') + '  skip     done, no further action', value: 'skip', short: 'skip' },
          ],
          default: 'skip',
        }).catch(() => 'skip')

        if (choice === 'review') {
          const { runCommand } = await import('./run-command.ts')
          const runCmd = runCommand()
          await runCmd.parseAsync(['node', 'nexarq'], { from: 'user' })
        } else if (choice === 'commit') {
          const { commitCommand } = await import('./commit-command.ts')
          const commitCmd = commitCommand()
          await commitCmd.parseAsync(['node', 'nexarq'], { from: 'user' })
        }
      }
    } catch (codeError) {
      if (tuiAlive) { tui.destroy(); tuiAlive = false }
      printError(codeError instanceof Error ? codeError.message : String(codeError))
      process.exit(1)
    }
  })

  return command
}

function printWorkflowReport(result: {
  planSummary: string
  subtasksCompleted: number
  reviewerOutput: string
  modifiedFiles: string[]
  durationMs: number
}): void {
  const cols = Math.max(process.stdout.columns ?? 80, 60)
  const ruleW = cols - 4
  const rule = chalk.gray('─'.repeat(ruleW))
  const subRule = chalk.gray('  ' + '─'.repeat(ruleW - 2))
  const elapsed = (result.durationMs / 1000).toFixed(1)

  console.log()
  console.log(rule)
  console.log(
    chalk.bold.cyan('  NEXARQ CODE REPORT') +
    chalk.gray(`  ·  ${result.subtasksCompleted} subtask(s)  ·  ${elapsed}s`)
  )
  console.log(rule)

  if (result.planSummary) {
    console.log()
    console.log(chalk.bold('  Plan'))
    console.log(subRule)
    console.log('    ' + result.planSummary)
  }

  if (result.reviewerOutput) {
    console.log()
    console.log(chalk.bold('  Review'))
    console.log(subRule)
    for (const line of result.reviewerOutput.trim().split('\n')) {
      console.log('    ' + line)
    }
  }

  if (result.modifiedFiles.length > 0) {
    console.log()
    console.log(chalk.bold('  Modified files'))
    console.log(subRule)
    for (const f of result.modifiedFiles) {
      console.log(chalk.green(`    ✓ ${f}`))
    }
  }

  console.log()
  console.log(rule)
}
