#!/usr/bin/env bun
import { Command } from 'commander'
import { chatCommand }    from './commands/chat-command.ts'
import { codeCommand }    from './commands/code-command.ts'
import { commitCommand }  from './commands/commit-command.ts'
import { configCommand }  from './commands/config-command.ts'
import { doctorCommand }  from './commands/doctor-command.ts'
import { explainCommand } from './commands/explain-command.ts'
import { fixCommand }     from './commands/fix-command.ts'
import { hookCommand }    from './commands/hook-command.ts'
import { ignoreCommand }  from './commands/ignore-command.ts'
import { initCommand }    from './commands/init-command.ts'
import { loginCommand }   from './commands/login-command.ts'
import { runCommand }     from './commands/run-command.ts'
import { watchCommand }   from './commands/watch-command.ts'
import { isFirstRun }     from './config/config-loader.ts'

const program = new Command()

program
  .name('nexarq')
  .description('Security-first, multi-agent code review for every git commit')
  .version('0.1.0')

// ── Default action: first-run shows welcome wizard, otherwise show help ────────
program.action(async () => {
  if (isFirstRun()) {
    // Lazy imports keep startup fast when a subcommand is used
    const { runWelcomeScreen }  = await import('./output/tui/welcome-tui.ts')
    const { runInitWizard }     = await import('./output/tui/init-tui.ts')
    const { getThemeByVariant } = await import('./output/tui/theme.ts')
    const { saveConfig }        = await import('./config/config-loader.ts')
    const { storeApiKey }       = await import('./auth/keyring.ts')
    const { installHook }       = await import('./git/hook-installer.ts')
    try {
      const variant = await runWelcomeScreen()
      const theme   = getThemeByVariant(variant)
      const wizard  = await runInitWizard(theme)

      if (wizard.apiKey) await storeApiKey(wizard.provider, wizard.apiKey)

      await saveConfig({
        provider:     wizard.provider,
        cloudConsent: wizard.cloudConsent,
        theme:        variant,
      })

      if (wizard.installPostCommit) await installHook('post-commit')
      if (wizard.installPrePush)    await installHook('pre-push')
    } catch (err) {
      const { printError } = await import('./output/formatter.ts')
      printError(err instanceof Error ? err.message : String(err))
      process.exit(1)
    }
  } else {
    program.help()
  }
})

// ── Core review & coding ──────────────────────────────────────────────────────
program.addCommand(runCommand())
program.addCommand(codeCommand())

// ── Productivity commands ─────────────────────────────────────────────────────
program.addCommand(commitCommand())
program.addCommand(fixCommand())
program.addCommand(watchCommand())
program.addCommand(explainCommand())
program.addCommand(chatCommand())
program.addCommand(ignoreCommand())

// ── Setup & config ────────────────────────────────────────────────────────────
program.addCommand(initCommand())
program.addCommand(hookCommand())
program.addCommand(configCommand())
program.addCommand(loginCommand())
program.addCommand(doctorCommand())

program.parse()
