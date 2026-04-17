import { Command } from 'commander'
import { detectAvailableProviders } from '@nexarq/agent-runtime'
import { loadConfig } from '../config/config-loader.ts'
import { getHookStatus } from '../git/hook-installer.ts'
import chalk from 'chalk'
import { execSync } from 'child_process'

export function doctorCommand(): Command {
  return new Command('doctor')
    .description('Check your Nexarq installation and configuration')
    .action(async () => {
      console.log(chalk.cyan('\nNexarq Doctor\n'))

      const checks: Array<{ label: string; pass: boolean; detail?: string }> = []

      // Node / Bun version
      const nodeVersion = process.version
      checks.push({
        label: 'Runtime',
        pass: true,
        detail: `Node.js ${nodeVersion}`,
      })

      // Git available
      try {
        const gitVersion = execSync('git --version', { encoding: 'utf-8' }).trim()
        checks.push({ label: 'Git', pass: true, detail: gitVersion })
      } catch {
        checks.push({ label: 'Git', pass: false, detail: 'git not found in PATH' })
      }

      // Config
      const config = await loadConfig()
      checks.push({
        label: 'Config',
        pass: true,
        detail: `provider=${config.provider}, model=${config.model ?? 'auto'}`,
      })

      // Provider health
      const availableProviders = await detectAvailableProviders()
      checks.push({
        label: 'LLM Provider',
        pass: availableProviders.includes(config.provider ?? 'ollama'),
        detail: availableProviders.length > 0
          ? `Available: ${availableProviders.join(', ')}`
          : 'No providers reachable — check API keys or start Ollama',
      })

      // Git hooks
      const hookStatus = await getHookStatus()
      const installedHooks = Object.entries(hookStatus)
        .filter(([, isInstalled]) => isInstalled)
        .map(([hookName]) => hookName)
      checks.push({
        label: 'Git Hooks',
        pass: installedHooks.length > 0,
        detail: installedHooks.length > 0
          ? installedHooks.join(', ')
          : 'No hooks installed — run `nexarq hook install post-commit`',
      })

      // Print results
      for (const { label, pass, detail } of checks) {
        const icon = pass ? chalk.green('✓') : chalk.red('✗')
        const labelText = label.padEnd(16)
        const detailText = detail ? chalk.gray(detail) : ''
        console.log(`  ${icon}  ${labelText} ${detailText}`)
      }

      const allPassed = checks.every((check) => check.pass)
      console.log(
        allPassed
          ? chalk.green('\nAll checks passed.\n')
          : chalk.yellow('\nSome checks failed. See details above.\n')
      )
    })
}
