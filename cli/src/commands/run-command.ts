import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { join, relative } from 'node:path'
import { Command } from 'commander'
import { runOrchestrator } from '@nexarq/agent-runtime'
import { extractDiff } from '../git/diff-extractor.ts'
import { parseDiff } from '../git/diff-parser.ts'
import { loadConfig } from '../config/config-loader.ts'
import { printError } from '../output/formatter.ts'
import { createSpinner } from '../output/spinner.ts'
import { createRunTUI } from '../output/tui/run-tui.ts'
import { createTuiEventHandler } from '../output/tui/tui-event-handler.ts'
import { approveEdit, createEditSession } from '../lib/edit-approval.ts'
import type { TriggerSource } from '@nexarq/agent-runtime'
import { select } from '@inquirer/prompts'
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
          onEvent: (event) => {
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
    const { onEvent } = createTuiEventHandler(tui)

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
        onEvent,
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

      // ── Inline fix prompt (no separate FIX window) ───────────────────────
      const actionable = result.results.filter((r) => {
        if (r.error) return false
        const out = r.output.trim()
        if (!out) return false
        if (!['critical', 'high', 'medium'].includes(r.severity)) return false
        const lines = out.split('\n').map((l) => l.trim()).filter(Boolean)
        return !lines.some((l) => /^NO FINDINGS$/i.test(l))
      })

      if (options.fix !== false && actionable.length > 0) {
        const sev = actionable.reduce((acc, r) => {
          acc[r.severity] = (acc[r.severity] ?? 0) + 1
          return acc
        }, {} as Record<string, number>)
        const sevStr = Object.entries(sev)
          .sort((a, b) => ['critical','high','medium','low','info'].indexOf(a[0]) - ['critical','high','medium','low','info'].indexOf(b[0]))
          .map(([s, n]) => (SEV_COLOR[s] ?? chalk.gray)(`${n} ${s}`))
          .join(chalk.gray('  ·  '))

        console.log()
        console.log(chalk.gray('  ──  ') + chalk.bold('Apply fixes?') + chalk.gray(`  ${sevStr}`))
        console.log()

        const choice = await select({
          message: 'Choose an action',
          choices: [
            { name: chalk.green('✓') + `  apply    apply all ${actionable.length} fix(es) now`,  value: 'apply',  short: 'apply'  },
            { name: chalk.cyan('⟳') + '  review   step through each fix before applying',         value: 'review', short: 'review' },
            { name: chalk.gray('·') + '  skip     continue without fixing',                        value: 'skip',   short: 'skip'   },
          ],
          default: 'skip',
        }).catch(() => 'skip')

        if (choice !== 'skip') {
          // Parse FINDING:/SUGGESTION: pairs directly from review agent output —
          // no extra agent call needed.
          interface ParsedFix {
            agentName: string
            file: string
            line: number
            message: string
            suggestion: string
          }
          const fixes: ParsedFix[] = []

          for (const r of actionable) {
            const lines = r.output.split('\n')
            for (let i = 0; i < lines.length; i++) {
              const m = (lines[i] ?? '').match(/^FINDING:\s+(\S+?):(\d+)\s+[—–-]+\s+(.+)$/)
              if (!m) continue
              let suggestion = ''
              for (let j = i + 1; j < Math.min(i + 5, lines.length); j++) {
                const s = (lines[j] ?? '').trim()
                if (s.startsWith('SUGGESTION:')) {
                  suggestion = s.replace(/^SUGGESTION:\s*/, '').trim()
                  break
                }
              }
              if (suggestion) {
                fixes.push({ agentName: r.agentName, file: m[1]!, line: parseInt(m[2]!), message: m[3]!, suggestion })
              }
            }
          }

          if (fixes.length === 0) {
            console.log(chalk.gray('  No file-specific suggestions found. Review the findings above.'))
          } else {
            // Deduplicate: one fix per file (first finding wins)
            const seen = new Set<string>()
            const dedupedFixes = fixes.filter((f) => {
              if (seen.has(f.file)) return false
              seen.add(f.file)
              return true
            })

            const session = createEditSession()
            if (choice === 'apply') session.approveAll = true

            for (const fix of dedupedFixes) {
              console.log()
              console.log(chalk.gray(`  ── ${fix.agentName}  `) + chalk.bold(`${fix.file}:${fix.line}`))
              console.log(`  ${fix.message}`)
              console.log()
              console.log(chalk.cyan('  Fix: ') + fix.suggestion)

              const fullPath = join(process.cwd(), fix.file)
              if (!existsSync(fullPath)) {
                console.log(chalk.gray(`  (file not found: ${fix.file})`))
                continue
              }

              const existing = readFileSync(fullPath, 'utf-8')
              const fileLines = existing.split('\n')

              // Insert a targeted TODO comment at the exact line, not at the top of the file
              const commentPrefix = fullPath.endsWith('.py') ? '# ' : '// '
              const insertAt = Math.min(Math.max(fix.line - 1, 0), fileLines.length)
              const todoLine = `${commentPrefix}nexarq (${fix.agentName}): ${fix.suggestion}`
              const newLines = [...fileLines]
              newLines.splice(insertAt, 0, todoLine)
              const newContent = newLines.join('\n')

              const displayPath = relative(process.cwd(), fullPath).replace(/\\/g, '/')
              const decision = await approveEdit({ displayPath, fullPath, line: fix.line, oldContent: existing, newContent, session })
              if (decision === 'yes') {
                writeFileSync(fullPath, newContent, 'utf-8')
                console.log(`  Applied fix to ${fix.file}`)
              } else {
                console.log(`  Skipped ${fix.file}`)
              }
            }
          }
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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const SEV_COLOR: Record<string, any> = {
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

// Used in hook mode (no TUI available)
function printDetailedReport(results: Array<{ error?: string; output: string; severity: string; agentName: string }>, durationMs: number): void {
  const cols = Math.max(process.stdout.columns ?? 80, 60)
  const ruleW = cols - 4
  const rule = chalk.gray('─'.repeat(ruleW))
  const elapsed = (durationMs / 1000).toFixed(1)

  console.log()
  console.log(rule)
  console.log(chalk.bold.cyan('  NEXARQ REVIEW REPORT') + chalk.gray(`  ·  ${results.length} agents  ·  ${elapsed}s`))
  console.log(rule)

  const order = ['critical', 'high', 'medium', 'low', 'info']
  const sorted = [...results].sort((a, b) => order.indexOf(a.severity) - order.indexOf(b.severity))

  for (const result of sorted) {
    if (result.error) continue
    const output = result.output.trim()
    if (!output) continue
    const color = SEV_COLOR[result.severity] ?? chalk.gray
    console.log()
    console.log(color(`  [${result.severity.toUpperCase().padEnd(8)}]  `) + chalk.bold(result.agentName))
    console.log(chalk.gray('  ' + '─'.repeat(ruleW - 2)))
    for (const line of output.split('\n')) {
      console.log('    ' + line)
    }
  }

  console.log()
  console.log(rule)
}

