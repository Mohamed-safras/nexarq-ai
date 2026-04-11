import { tool } from '@langchain/core/tools'
import { z } from 'zod'
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs'
import { resolve, dirname } from 'path'
import { execSync } from 'child_process'

const MAX_WRITE_SIZE_BYTES = 500_000
const COMMAND_TIMEOUT_MS = 60_000

/**
 * Prefix-based allowlist — command must START WITH one of these strings.
 * Prevents arbitrary shell execution while allowing common dev workflows.
 */
const ALLOWED_COMMAND_PREFIXES: readonly string[] = [
  // Test runners
  'pytest', 'python -m pytest',
  'npm test', 'npm run test',
  'bun test', 'bun run test',
  'go test',
  'cargo test',
  'jest', 'vitest', 'mocha',
  // Linters and formatters
  'ruff check', 'ruff format',
  'eslint', 'prettier --write', 'prettier --check',
  'tsc', 'tsc --noEmit',
  'mypy', 'pyright',
  'biome check', 'biome format',
  'golangci-lint run',
  // Build
  'npm run build', 'bun run build',
  'go build', 'cargo build',
  // Safe read-only git commands
  'git status', 'git log', 'git diff', 'git show', 'git branch',
]

function isCommandAllowed(command: string): boolean {
  const trimmedCommand = command.trim()
  return ALLOWED_COMMAND_PREFIXES.some((allowedPrefix) =>
    trimmedCommand.startsWith(allowedPrefix)
  )
}

/**
 * Read-write tools available ONLY to the coding-agent node.
 * Review agents receive only the read-only tools from review-tools.ts.
 */
export function getCodingTools(workingDirectory: string) {
  const safeResolve = (filePath: string): string => {
    const absolutePath = resolve(workingDirectory, filePath)
    if (!absolutePath.startsWith(resolve(workingDirectory))) {
      throw new Error(`Path traversal blocked: "${filePath}"`)
    }
    return absolutePath
  }

  const writeFileTool = tool(
    async ({ filePath, content }: { filePath: string; content: string }): Promise<string> => {
      const absolutePath = safeResolve(filePath)

      if (Buffer.byteLength(content, 'utf-8') > MAX_WRITE_SIZE_BYTES) {
        return `[BLOCKED] Content exceeds the ${MAX_WRITE_SIZE_BYTES}-byte limit.`
      }

      // Always back up the existing file before overwriting
      if (existsSync(absolutePath)) {
        const existingContent = readFileSync(absolutePath, 'utf-8')
        writeFileSync(`${absolutePath}.nexarq-backup`, existingContent, 'utf-8')
      }

      mkdirSync(dirname(absolutePath), { recursive: true })
      writeFileSync(absolutePath, content, 'utf-8')

      return `Written ${content.length} chars to "${filePath}".`
    },
    {
      name: 'write_file',
      description:
        'Write or overwrite a file. Creates parent directories automatically. ' +
        'Saves a .nexarq-backup copy of any existing content before writing.',
      schema: z.object({
        filePath: z.string().describe('Relative path from project root'),
        content:  z.string().describe('Full file content to write'),
      }),
    }
  )

  const runCommandTool = tool(
    async ({ command }: { command: string }): Promise<string> => {
      if (!isCommandAllowed(command)) {
        return (
          `[BLOCKED] "${command}" is not on the allowed list.\n` +
          `Allowed prefixes: ${ALLOWED_COMMAND_PREFIXES.join(', ')}`
        )
      }

      try {
        const output = execSync(command, {
          cwd: workingDirectory,
          encoding: 'utf-8',
          timeout: COMMAND_TIMEOUT_MS,
        })
        return output.trim() || '(command completed with no output)'
      } catch (caughtError) {
        const errorDetails = caughtError as {
          stdout?: string
          stderr?: string
          message?: string
        }
        return [errorDetails.stdout, errorDetails.stderr, errorDetails.message]
          .filter(Boolean)
          .join('\n')
          .trim()
      }
    },
    {
      name: 'run_command',
      description:
        'Run an allowed shell command such as a test runner or linter. ' +
        'Arbitrary shell commands are blocked for safety.',
      schema: z.object({
        command: z.string().describe('The command to execute'),
      }),
    }
  )

  const gitDiffTool = tool(
    async ({ target }: { target?: string }): Promise<string> => {
      try {
        const diffTarget = target ?? 'HEAD'
        const output = execSync(`git diff ${diffTarget}`, {
          cwd: workingDirectory,
          encoding: 'utf-8',
          timeout: 5_000,
        })
        return output.trim() || '(no changes)'
      } catch {
        return 'Unable to read git diff.'
      }
    },
    {
      name: 'git_diff',
      description: 'Show the current working-tree diff against HEAD or another ref.',
      schema: z.object({
        target: z.string().optional().describe('Git ref to diff against (default: HEAD)'),
      }),
    }
  )

  const gitStatusTool = tool(
    async (): Promise<string> => {
      try {
        const output = execSync('git status --short', {
          cwd: workingDirectory,
          encoding: 'utf-8',
          timeout: 5_000,
        })
        return output.trim() || '(working tree clean)'
      } catch {
        return 'Unable to read git status.'
      }
    },
    {
      name: 'git_status',
      description: 'Show the current working tree status (modified, untracked files).',
      schema: z.object({}),
    }
  )

  return [writeFileTool, runCommandTool, gitDiffTool, gitStatusTool]
}
