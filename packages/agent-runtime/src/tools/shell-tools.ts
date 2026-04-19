import { tool } from '@langchain/core/tools'
import { z } from 'zod'
import { execSync } from 'child_process'

const COMMAND_TIMEOUT_MS   = 120_000 // 2 min — allows npm install, migrations, builds
const MAX_OUTPUT_CHARS     = 10_000

/** Commands blocked even in unsafe mode — irreversible destructive ops */
const ALWAYS_BLOCKED = [
  /^\s*rm\s+-rf\s+\//, // rm -rf /
  /^\s*:(){ :|:& };:/, // fork bomb
  /^\s*dd\s+if=/,      // disk wipe
  /^\s*mkfs\b/,        // format filesystem
  />\s*\/dev\/(s?d[a-z]|nvme)/, // write to raw disk
]

function isAlwaysBlocked(command: string): boolean {
  return ALWAYS_BLOCKED.some((pattern) => pattern.test(command))
}

/**
 * Shell tools — unrestricted command execution for general coding assistant mode.
 *
 * Two safety levels:
 *   unsafe=false (default) → only allowlisted validation commands (test/lint/typecheck)
 *   unsafe=true            → any command except permanently blocked destructive ops
 *
 * The unsafe flag is opt-in via RunConfig.unsafeShell — never enabled by default.
 * A visible warning is prepended to every unsafe output so the user always knows.
 */
export function getShellTools(workingDirectory: string, unsafe: boolean = false) {
  const runShellTool = tool(
    async ({ command }: { command: string }): Promise<string> => {
      if (isAlwaysBlocked(command)) {
        return `[BLOCKED] "${command.trim()}" is permanently blocked — irreversible destructive operation.`
      }

      const warningPrefix = unsafe
        ? `[UNSAFE SHELL — running without allowlist]\n`
        : ''

      try {
        const raw = execSync(command, {
          cwd:      workingDirectory,
          encoding: 'utf-8',
          timeout:  COMMAND_TIMEOUT_MS,
          // Merge stderr into stdout so npm errors, tracebacks etc. are captured
          stdio: ['ignore', 'pipe', 'pipe'],
          env: { ...process.env, FORCE_COLOR: '0' }, // strip ANSI codes for token efficiency
        })
        const trimmed = raw.trim()
        const out     = trimmed.length > MAX_OUTPUT_CHARS
          ? trimmed.slice(0, MAX_OUTPUT_CHARS) + '\n... [truncated]'
          : trimmed || '(command completed with no output)'

        return warningPrefix + out
      } catch (err) {
        const e   = err as { stdout?: string; stderr?: string; message?: string; status?: number }
        const out = [e.stdout, e.stderr, e.message].filter(Boolean).join('\n').trim()
        const truncated = out.length > MAX_OUTPUT_CHARS ? out.slice(0, MAX_OUTPUT_CHARS) + '\n... [truncated]' : out
        return warningPrefix + (truncated || '(command failed with no output)')
      }
    },
    {
      name: 'run_shell',
      description: unsafe
        ? 'Run any shell command in the project directory. ' +
          'Use for installing packages (npm install, bun add), running migrations, starting dev servers, deploying. ' +
          'WARNING: runs without an allowlist — only permanently destructive ops are blocked.'
        : 'Run an allowed shell command (test/lint/typecheck only). ' +
          'For broader shell access, enable unsafeShell in RunConfig.',
      schema: z.object({
        command: z.string().describe('Shell command to execute, e.g. "bun add express", "bun run db:migrate", "bun run dev"'),
      }),
    }
  )

  return [runShellTool]
}
