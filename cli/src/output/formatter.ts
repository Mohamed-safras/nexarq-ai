import chalk from 'chalk'
import type { AgentResult, RunSummary } from '@nexarq/common/interfaces'

const SEVERITY_COLOR: Record<string, (text: string) => string> = {
  critical: (text) => chalk.bold.red(text),
  high:     (text) => chalk.red(text),
  medium:   (text) => chalk.yellow(text),
  low:      (text) => chalk.cyan(text),
  info:     (text) => chalk.gray(text),
}

export function printHeader(rawDiff: string): void {
  const lineCount = rawDiff.split('\n').length
  console.log()
  console.log(chalk.cyan('  Nexarq') + chalk.gray(` — ${lineCount} diff lines`))
  console.log(chalk.gray('  ' + '─'.repeat(50)))
  console.log()
}

export function printAgentResult(result: AgentResult): void {
  if (!result.output.trim() && !result.error) return

  const colorFn = SEVERITY_COLOR[result.severity] ?? SEVERITY_COLOR['info']!
  const label = colorFn(`[${result.severity.toUpperCase()}]`)
  const agentLabel = chalk.bold(result.agentName)

  if (result.error) {
    console.log(`  ${label} ${agentLabel} — ${chalk.gray(result.error)}`)
    return
  }

  console.log(`  ${label} ${agentLabel}`)
  const outputLines = result.output.trim().split('\n')
  for (const line of outputLines) {
    console.log(`    ${chalk.gray(line)}`)
  }
  console.log()
}

export function printSummary(summary: RunSummary): void {
  console.log(chalk.gray('  ' + '─'.repeat(50)))
  console.log()

  const counts = [
    summary.critical > 0 ? chalk.bold.red(`${summary.critical} critical`) : null,
    summary.high     > 0 ? chalk.red(`${summary.high} high`)             : null,
    summary.medium   > 0 ? chalk.yellow(`${summary.medium} medium`)      : null,
    summary.low      > 0 ? chalk.cyan(`${summary.low} low`)              : null,
    summary.info     > 0 ? chalk.gray(`${summary.info} info`)            : null,
  ].filter(Boolean)

  if (counts.length === 0) {
    console.log('  ' + chalk.green('No issues found.'))
  } else {
    console.log('  ' + counts.join(chalk.gray(' · ')))
  }

  const tokensText = chalk.gray(`${summary.tokensUsed.toLocaleString()} tokens`)
  const agentsText = chalk.gray(`${summary.agentsRun.length} agents`)
  console.log(`  ${agentsText} · ${tokensText}`)
  console.log()
}

export function printError(message: string): void {
  console.error(chalk.red(`  Error: ${message}`))
}
