import { Command } from 'commander'
import { runOrchestrator } from '@nexarq/agent-runtime'
import { extractDiff } from '../git/diff-extractor.ts'
import { parseDiff } from '../git/diff-parser.ts'
import { loadConfig } from '../config/config-loader.ts'
import { printError } from '../output/formatter.ts'
import { createSpinner } from '../output/spinner.ts'
import { createRunTUI } from '../output/tui/run-tui.ts'
import type { RunEvent, AgentResult } from '@nexarq/common/types'
import type { TriggerSource } from '@nexarq/agent-runtime'
import { confirm } from '@inquirer/prompts'
import chalk from 'chalk'

export function runCommand(): Command {
  const command = new Command('run')
    .description('Run code review on the latest commit or staged changes')
    .option('-a, --agents <names>', 'Comma-separated agent names to run')
    .option('-m, --mode <mode>',    'Execution mode: fast | smart | deep | auto', 'smart')
    .option('-d, --diff <file>',    'Path to a diff file instead of git diff')
    .option('--hook',               'Internal flag used by git hooks (compact output)')
    .option('--pre-push',           'Run in pre-push mode (tier 1 only, blocks on CRITICAL/HIGH)')
    .option('--list-agents',        'List all available agents and exit')
    .option('--no-fix',             'Skip the auto-apply prompt after findings')

  command.action(async (options: {
    agents?: string
    mode?: string
    diff?: string
    hook?: boolean
    prePush?: boolean
    listAgents?: boolean
    fix?: boolean
  }) => {
    const config = await loadConfig()

    if (options.listAgents) {
      const { getAllAgents } = await import('@nexarq/agent-runtime')
      for (const agentDef of getAllAgents()) {
        console.log(`  ${agentDef.name.padEnd(20)} [tier ${agentDef.tier}] ${agentDef.description}`)
      }
      return
    }

    const triggerSource: TriggerSource = options.prePush
      ? 'pre-push'
      : options.hook
        ? 'post-commit'
        : 'on-demand'

    // Respect per-repo autoRun disable (e.g. .nexarq/config.json → autoRun: false)
    if ((options.hook || options.prePush) && config.autoRun === false) {
      return
    }

    const isHookMode = Boolean(options.hook || options.prePush)
    const spinner    = isHookMode ? createSpinner('Extracting diff...') : null

    let rawDiff: string
    try {
      rawDiff = options.diff
        ? await Bun.file(options.diff).text()
        : await extractDiff(triggerSource)
    } catch (extractError) {
      spinner?.fail('Failed to extract diff')
      printError(extractError instanceof Error ? extractError.message : String(extractError))
      process.exit(1)
    }

    if (!rawDiff.trim()) {
      spinner?.info('No changes to review.')
      return
    }

    // ── Parse diff → proper DiffResult (drives agent selection) ──────────────
    const diffResult = parseDiff(rawDiff)
    const agentNames = options.agents?.split(',').map((n) => n.trim())

    if (isHookMode) {
      // ── Compact hook output ────────────────────────────────────────────────
      spinner!.start(`Reviewing ${diffResult.files.length} files (${diffResult.primaryLanguage}) [${diffResult.changeType}]...`)

      try {
        const result = await runOrchestrator({
          task: 'Review the following diff',
          diffResult,
          triggerSource,
          runConfig: {
            ...(agentNames ? { agents: agentNames } : {}),
            mode: options.mode as 'fast' | 'smart' | 'deep' | 'auto',
            provider: config.provider,
            ...(config.model ? { model: config.model } : {}),
          },
          onEvent: (event: RunEvent) => {
            if (event.type === 'agent:complete') {
              spinner!.text = `  ✓ ${event.result.agentName}`
            }
          },
        })

        spinner!.succeed(
          `Review done — ${result.results.length} agents, ${result.durationMs}ms` +
          formatSeveritySummary(result.summary)
        )

        printDetailedReport(result.results, result.durationMs)

        if (triggerSource === 'pre-push' && result.summary.critical + result.summary.high > 0) {
          printError(`Push blocked: ${result.summary.critical} critical, ${result.summary.high} high severity findings.`)
          printError('Fix the issues or set NEXARQ_SKIP=1 to bypass.')
          process.exit(1)
        }
      } catch (runError) {
        spinner!.fail('Review failed')
        printError(runError instanceof Error ? runError.message : String(runError))
        process.exit(1)
      }

      return
    }

    // ── Interactive TUI mode ─────────────────────────────────────────────────
    const tui = await createRunTUI(rawDiff.split('\n').length)

    let totalAgents = 0
    let doneAgents  = 0

    try {
      const result = await runOrchestrator({
        task: 'Review the following diff',
        diffResult,
        triggerSource,
        runConfig: {
          ...(agentNames ? { agents: agentNames } : {}),
          mode: options.mode as 'fast' | 'smart' | 'deep' | 'auto',
          provider: config.provider,
          ...(config.model ? { model: config.model } : {}),
        },
        onEvent: (event: RunEvent) => {
          if (event.type === 'run:plan') {
            totalAgents = event.agentNames.length
            tui.initAgents(event.agentNames)
          }
          if (event.type === 'agent:start') {
            tui.setAgentStatus(event.agentName, 'running')
          }
          if (event.type === 'agent:chunk') {
            tui.appendChunk(event.agentName, event.text)
          }
          if (event.type === 'agent:complete') {
            doneAgents++
            tui.setAgentStatus(event.result.agentName, event.result.error ? 'error' : 'done')
            const findingLines = event.result.output.trim().split('\n').filter(Boolean)
            if (findingLines.length > 0) {
              tui.addFinding(event.result.agentName, event.result.severity, findingLines)
            }
            tui.updateFooter(doneAgents, totalAgents, {}, 0)
          }
          if (event.type === 'agent:error') {
            tui.setAgentStatus(event.agentName, 'error')
          }
        },
      })

      tui.updateFooter(result.results.length, result.results.length, result.summary, result.summary.tokensUsed)
      tui.showComplete(result.durationMs)

      if (triggerSource === 'pre-push' && result.summary.critical + result.summary.high > 0) {
        await tui.waitForExit()
        tui.destroy()
        printError(`Push blocked: ${result.summary.critical} critical, ${result.summary.high} high findings.`)
        process.exit(1)
      }

      await tui.waitForExit()
      tui.destroy()

      // ── Full detailed report after TUI exits ─────────────────────────────
      printDetailedReport(result.results, result.durationMs)

      // ── Auto-apply prompt ────────────────────────────────────────────────
      const actionable = result.results.filter(
        (r) => !r.error && r.output.trim() &&
               (r.severity === 'critical' || r.severity === 'high' || r.severity === 'medium')
      )
      if (options.fix !== false && actionable.length > 0) {
        console.log()
        const shouldFix = await confirm({
          message: chalk.yellow(`Apply auto-fixes for ${actionable.length} finding(s)?`),
          default: false,
        }).catch(() => false)

        if (shouldFix) {
          const { fixCommand } = await import('./fix-command.ts')
          const fixCmd = fixCommand()
          await fixCmd.parseAsync(['node', 'nexarq', '--from-run'], { from: 'user' })
        }
      }
    } catch (runError) {
      tui.destroy()
      printError(runError instanceof Error ? runError.message : String(runError))
      process.exit(1)
    }
  })

  return command
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const SEV_COLOR: Record<string, chalk.Chalk> = {
  critical: chalk.bold.red,
  high:     chalk.red,
  medium:   chalk.yellow,
  low:      chalk.cyan,
  info:     chalk.gray,
}

function formatSeveritySummary(summary: { critical: number; high: number; medium: number; low: number; info: number }): string {
  const parts: string[] = []
  if (summary.critical) parts.push(chalk.bold.red(`  ${summary.critical} critical`))
  if (summary.high)     parts.push(chalk.red(`${summary.high} high`))
  if (summary.medium)   parts.push(chalk.yellow(`${summary.medium} medium`))
  if (summary.low)      parts.push(chalk.cyan(`${summary.low} low`))
  return parts.length ? '  ·  ' + parts.join('  ') : ''
}

function printDetailedReport(results: AgentResult[], durationMs: number): void {
  const cols = process.stdout.columns ?? 80
  const rule = chalk.gray('─'.repeat(Math.min(cols - 2, 72)))
  const elapsed = (durationMs / 1000).toFixed(1)

  console.log()
  console.log(rule)
  console.log(chalk.bold.cyan('  NEXARQ REVIEW REPORT') + chalk.gray(`  ·  ${results.length} agents  ·  ${elapsed}s`))
  console.log(rule)

  // Sort by severity: critical → high → medium → low → info
  const order = ['critical', 'high', 'medium', 'low', 'info']
  const sorted = [...results].sort(
    (a, b) => order.indexOf(a.severity) - order.indexOf(b.severity)
  )

  for (const result of sorted) {
    if (result.error) continue
    const output = result.output.trim()
    if (!output) continue

    const color = SEV_COLOR[result.severity] ?? chalk.gray
    console.log()
    console.log(color(`  [${result.severity.toUpperCase().padEnd(8)}]  `) + chalk.bold(result.agentName))
    console.log(chalk.gray('  ' + '─'.repeat(Math.min(cols - 4, 60))))

    // Print full output, indented 4 spaces
    for (const line of output.split('\n')) {
      console.log('    ' + line)
    }
  }

  console.log()
  console.log(rule)
}
