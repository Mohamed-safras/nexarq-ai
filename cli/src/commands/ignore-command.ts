import { Command } from 'commander'
import { createIgnoreStore } from '../config/ignore-store.ts'
import { printError } from '../output/formatter.ts'
import chalk from 'chalk'

/**
 * nexarq ignore
 *
 * Manage the .nexarq/ignore.json file — suppress known/accepted findings
 * by their fingerprint so they're never reported again.
 *
 * Usage:
 *   nexarq ignore add <fingerprint> --reason "accepted risk"
 *   nexarq ignore list
 *   nexarq ignore remove <fingerprint>
 */
export function ignoreCommand(): Command {
  const command = new Command('ignore')
    .description('Manage suppressed findings (.nexarq/ignore.json)')

  command
    .command('add <fingerprint>')
    .description('Suppress a finding by its fingerprint ID')
    .option('-r, --reason <text>', 'Why this finding is acceptable')
    .action((fingerprint: string, options: { reason?: string }) => {
      const store = createIgnoreStore(process.cwd())
      store.ignore(fingerprint, options.reason)
      console.log(chalk.green(`  Ignored: ${fingerprint}`))
      if (options.reason) console.log(chalk.gray(`  Reason: ${options.reason}`))
      console.log(chalk.gray('  Commit .nexarq/ignore.json to share with your team.'))
    })

  command
    .command('list')
    .description('List all suppressed findings')
    .action(() => {
      const store = createIgnoreStore(process.cwd())
      const entries = store.list()

      if (entries.length === 0) {
        console.log(chalk.gray('  No ignored findings.'))
        return
      }

      console.log()
      for (const entry of entries) {
        console.log(`  ${chalk.yellow(entry.fingerprint)}`)
        if (entry.reason) console.log(`    ${chalk.gray('Reason: ' + entry.reason)}`)
        console.log(`    ${chalk.gray('Ignored: ' + new Date(entry.ignoredAt).toLocaleDateString())}`)
      }
      console.log()
    })

  command
    .command('remove <fingerprint>')
    .description('Remove a suppression — finding will be reported again')
    .action((fingerprint: string) => {
      const store = createIgnoreStore(process.cwd())
      const entries = store.list()
      const exists = entries.some((entry) => entry.fingerprint === fingerprint)

      if (!exists) {
        printError(`Fingerprint not found: ${fingerprint}`)
        process.exit(1)
      }

      // Rewrite without the removed entry
      const { writeFileSync, mkdirSync } = require('node:fs')
      const { join, dirname } = require('node:path')
      const filePath = join(process.cwd(), '.nexarq/ignore.json')
      const updated = { version: 1, ignored: entries.filter((entry) => entry.fingerprint !== fingerprint) }
      mkdirSync(dirname(filePath), { recursive: true })
      writeFileSync(filePath, JSON.stringify(updated, null, 2) + '\n', 'utf-8')
      console.log(chalk.green(`  Removed: ${fingerprint}`))
    })

  return command
}
