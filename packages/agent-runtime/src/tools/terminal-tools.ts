import { tool } from '@langchain/core/tools'
import { z } from 'zod'
import { execSync } from 'child_process'

const COMMAND_TIMEOUT_MS = 60_000
const MAX_OUTPUT_CHARS   = 8_000

/**
 * Commands the triage node and conversation orchestrator are allowed to run.
 * Covers validation workflows only — no file writes, no network, no destructive ops.
 */
const ALLOWED_PREFIXES: readonly string[] = [
  'tsc', 'tsc --noEmit',
  'bun test', 'bun run test', 'bun run typecheck', 'bun run lint', 'bun run check',
  'npm test', 'npm run test', 'npm run typecheck', 'npm run lint', 'npm run build',
  'pnpm test', 'pnpm run test', 'pnpm run typecheck', 'pnpm run lint',
  'jest', 'vitest', 'mocha',
  'cargo test', 'cargo check', 'cargo clippy',
  'go test', 'go vet', 'go build',
  'pytest', 'python -m pytest',
  'ruff check', 'mypy', 'pyright',
  'eslint', 'biome check',
  'golangci-lint run',
]

function isAllowed(command: string): boolean {
  const trimmed = command.trim()
  return ALLOWED_PREFIXES.some((prefix) => trimmed === prefix || trimmed.startsWith(prefix + ' '))
}

/**
 * Terminal tools for the triage node and conversation orchestrator.
 * Read-only in terms of filesystem — only runs validation commands.
 * Never allows writes, pushes, or arbitrary shell execution.
 */
export function getTerminalTools(workingDirectory: string) {
  const runValidationTool = tool(
    async ({ command }: { command: string }): Promise<string> => {
      if (!isAllowed(command)) {
        return (
          `[BLOCKED] "${command.trim()}" is not on the validation allowlist.\n` +
          `Allowed prefixes: ${ALLOWED_PREFIXES.slice(0, 8).join(', ')}, ...`
        )
      }
      try {
        const raw = execSync(command, {
          cwd: workingDirectory,
          encoding: 'utf-8',
          timeout: COMMAND_TIMEOUT_MS,
          // Merge stderr into stdout so linter/compiler errors are captured
          stdio: ['ignore', 'pipe', 'pipe'],
        })
        const trimmed = raw.trim()
        return trimmed.length > MAX_OUTPUT_CHARS
          ? trimmed.slice(0, MAX_OUTPUT_CHARS) + '\n... [truncated]'
          : trimmed || '(command completed with no output)'
      } catch (err) {
        const e = err as { stdout?: string; stderr?: string; message?: string }
        const out = [e.stdout, e.stderr, e.message].filter(Boolean).join('\n').trim()
        return out.length > MAX_OUTPUT_CHARS ? out.slice(0, MAX_OUTPUT_CHARS) + '\n... [truncated]' : out
      }
    },
    {
      name: 'run_validation',
      description:
        'Run a validation command (typecheck, tests, lint) to verify whether a finding is real ' +
        'or to confirm that suggested fixes compile. Only test/lint/typecheck commands are allowed.',
      schema: z.object({
        command: z.string().describe('Validation command to run, e.g. "tsc --noEmit" or "bun test"'),
      }),
    }
  )

  return [runValidationTool]
}
