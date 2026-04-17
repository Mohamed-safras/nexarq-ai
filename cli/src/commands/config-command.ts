import { Command } from 'commander'
import { loadConfig, saveConfig, showConfig } from '../config/config-loader.ts'
import chalk from 'chalk'

export function configCommand(): Command {
  const command = new Command('config')
    .description('View and update Nexarq configuration')

  command
    .command('show')
    .description('Show current configuration')
    .action(async () => {
      const config = await loadConfig()
      showConfig(config)
    })

  command
    .command('set-provider <provider>')
    .description('Set the default LLM provider: ollama | openai | anthropic | google')
    .option('--model <model>', 'Set the default model for this provider')
    .action(async (provider: string, options: { model?: string }) => {
      const config = await loadConfig()
      await saveConfig({ ...config, provider: provider as 'ollama' | 'openai' | 'anthropic' | 'google', ...(options.model ? { model: options.model } : {}) })
      console.log(chalk.green(`  Provider set to ${provider}${options.model ? ` (${options.model})` : ''}`))
    })

  command
    .command('set-agents <agents>')
    .description('Set default agents as a comma-separated list')
    .action(async (agents: string) => {
      const config = await loadConfig()
      const agentList = agents.split(',').map((name) => name.trim())
      await saveConfig({ ...config, defaultAgents: agentList })
      console.log(chalk.green(`  Default agents: ${agentList.join(', ')}`))
    })

  command
    .command('cloud-consent <value>')
    .description('Allow sending diffs to cloud LLMs: true | false')
    .action(async (value: string) => {
      const config = await loadConfig()
      const cloudConsent = value === 'true'
      await saveConfig({ ...config, cloudConsent })
      console.log(chalk.green(`  Cloud consent: ${cloudConsent}`))
    })

  command
    .command('auto-run <value>')
    .description('Enable/disable auto-run after commit/push: true | false')
    .option('--repo', 'Apply to current repo only (writes .nexarq/config.json)')
    .action(async (value: string, options: { repo?: boolean }) => {
      const autoRun = value === 'true' || value === 'enable' || value === 'on'
      if (options.repo) {
        // Per-repo config
        const { join } = await import('path')
        const { mkdirSync, writeFileSync, existsSync, readFileSync } = await import('fs')
        const repoConfigDir  = join(process.cwd(), '.nexarq')
        const repoConfigPath = join(repoConfigDir, 'config.json')
        mkdirSync(repoConfigDir, { recursive: true })
        const existing = existsSync(repoConfigPath)
          ? JSON.parse(readFileSync(repoConfigPath, 'utf-8'))
          : {}
        writeFileSync(repoConfigPath, JSON.stringify({ ...existing, autoRun }, null, 2), 'utf-8')
        console.log(chalk.green(`  Auto-run ${autoRun ? 'enabled' : 'disabled'} for this repo (.nexarq/config.json)`))
      } else {
        const config = await loadConfig()
        await saveConfig({ ...config, autoRun })
        console.log(chalk.green(`  Auto-run ${autoRun ? 'enabled' : 'disabled'} globally (~/.nexarq/config.json)`))
      }
    })

  return command
}
