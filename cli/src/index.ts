#!/usr/bin/env bun
import { Command } from 'commander'
import { chatCommand } from './commands/chat-command.ts'
import { codeCommand } from './commands/code-command.ts'
import { commitCommand } from './commands/commit-command.ts'
import { configCommand } from './commands/config-command.ts'
import { doctorCommand } from './commands/doctor-command.ts'
import { explainCommand } from './commands/explain-command.ts'
import { fixCommand } from './commands/fix-command.ts'
import { hookCommand } from './commands/hook-command.ts'
import { ignoreCommand } from './commands/ignore-command.ts'
import { initCommand } from './commands/init-command.ts'
import { loginCommand } from './commands/login-command.ts'
import { runCommand } from './commands/run-command.ts'
import { watchCommand } from './commands/watch-command.ts'
import { isFirstRun } from './config/config-loader.ts'

const program = new Command()

program
  .name('nexarq')
  .description('multi-agent code review and coding assistant')
  .version('0.1.0')

/**
 * Default action (no subcommand):
 *   1st run  → init wizard, then interactive session
 *   returning → interactive session directly
 */
program.action(async () => {
  if (isFirstRun()) {
    const { safeRunInitFlow } = await import('./init/run-init-flow.ts')
    const ok = await safeRunInitFlow()
    if (!ok) process.exit(1)
  }
  const { runInteractiveSession } = await import('./session/interactive-session.ts')
  await runInteractiveSession()
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
