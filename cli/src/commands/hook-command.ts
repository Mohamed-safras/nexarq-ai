import { Command } from 'commander'
import { installHook, uninstallHook, getHookStatus } from '../git/hook-installer.ts'
import { printError } from '../output/formatter.ts'
import chalk from 'chalk'

export function hookCommand(): Command {
  const command = new Command('hook')
    .description('Manage Nexarq git hooks')

  command
    .command('install <type>')
    .description('Install a git hook: post-commit | pre-push')
    .action(async (hookType: string) => {
      if (hookType !== 'post-commit' && hookType !== 'pre-push') {
        printError(`Unknown hook type "${hookType}". Use: post-commit, pre-push`)
        process.exit(1)
      }
      await installHook(hookType as 'post-commit' | 'pre-push')
      console.log(chalk.green(`  ${hookType} hook installed.`))
    })

  command
    .command('uninstall <type>')
    .description('Remove a Nexarq git hook')
    .action(async (hookType: string) => {
      await uninstallHook(hookType as 'post-commit' | 'pre-push')
      console.log(chalk.green(`  ${hookType} hook removed.`))
    })

  command
    .command('status')
    .description('Show which git hooks are currently installed')
    .action(async () => {
      const status = await getHookStatus()
      for (const [hookName, isInstalled] of Object.entries(status)) {
        const indicator = isInstalled ? chalk.green('installed') : chalk.gray('not installed')
        console.log(`  ${hookName.padEnd(14)} ${indicator}`)
      }
    })

  return command
}
