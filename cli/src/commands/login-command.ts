import { Command } from 'commander'
import { startGitHubDeviceFlow } from '../auth/github-auth.ts'
import { printError } from '../output/formatter.ts'
import chalk from 'chalk'

export function loginCommand(): Command {
  return new Command('login')
    .description('Authenticate with GitHub (optional — for web dashboard sync)')
    .action(async () => {
      console.log(chalk.cyan('\nNexarq Login\n'))
      console.log('Nexarq works offline without login.')
      console.log('Login enables: run history, web dashboard, team sharing.\n')

      try {
        const result = await startGitHubDeviceFlow()
        console.log(chalk.green(`\nLogged in as ${chalk.bold(result.username)}`))
      } catch (loginError) {
        printError(loginError instanceof Error ? loginError.message : String(loginError))
        process.exit(1)
      }
    })
}
