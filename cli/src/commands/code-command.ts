import { Command } from 'commander'
import { runWorkflowOrchestrator } from '@nexarq/agent-runtime'
import { loadConfig } from '../config/config-loader.ts'
import { printError } from '../output/formatter.ts'
import { createRunTUI } from '../output/tui/run-tui.ts'
import { createTuiEventHandler } from '../output/tui/tui-event-handler.ts'
import chalk from 'chalk'

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

    try {
      const result = await runWorkflowOrchestrator({
        task,
        workingDirectory,
        runConfig: {
          provider: config.provider,
          ...(config.model ? { model: config.model } : {}),
        },
        onEvent,
      })

      tui.updateFooter(tuiState.totalAgents, tuiState.totalAgents, {}, 0)
      tui.showComplete(result.durationMs)

      await tui.waitForExit()
      tui.destroy()

      printWorkflowReport(result)
    } catch (codeError) {
      tui.destroy()
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
  const cols  = process.stdout.columns ?? 80
  const rule  = chalk.gray('─'.repeat(Math.min(cols - 2, 72)))
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
    console.log(chalk.gray('  ' + '─'.repeat(40)))
    console.log('    ' + result.planSummary)
  }

  if (result.reviewerOutput) {
    console.log()
    console.log(chalk.bold('  Review'))
    console.log(chalk.gray('  ' + '─'.repeat(40)))
    for (const line of result.reviewerOutput.trim().split('\n')) {
      console.log('    ' + line)
    }
  }

  if (result.modifiedFiles.length > 0) {
    console.log()
    console.log(chalk.bold('  Modified files'))
    console.log(chalk.gray('  ' + '─'.repeat(40)))
    for (const f of result.modifiedFiles) {
      console.log(chalk.green(`    ✓ ${f}`))
    }
  }

  console.log()
  console.log(rule)
}
