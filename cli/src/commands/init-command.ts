import { Command } from 'commander'
import { runInitFlow } from '../init/run-init-flow.ts'
import { printError } from '../output/formatter.ts'

export function initCommand(): Command {
  return new Command('init')
    .description('Interactive setup wizard — theme picker + provider config')
    .action(async () => {
      try {
        await runInitFlow()
      } catch (err) {
        printError(err instanceof Error ? err.message : String(err))
        process.exit(1)
      }
    })
}
