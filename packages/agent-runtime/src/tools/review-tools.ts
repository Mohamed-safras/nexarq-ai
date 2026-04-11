import { tool } from '@langchain/core/tools'
import { z } from 'zod'
import { readFileSync, readdirSync, existsSync } from 'fs'
import { join, resolve, relative } from 'path'
import { execSync } from 'child_process'
import { BLOCKED_FILE_NAMES, ALLOWED_EXTENSIONS } from '@nexarq/common/constants'

const MAX_FILE_OUTPUT_CHARS = 8_000
const MAX_SEARCH_RESULTS = 40
const MAX_COMMAND_OUTPUT_CHARS = 6_000

/**
 * Read-only tools available to ALL agents (review + coding-agent).
 * These never modify the filesystem or execute arbitrary code.
 */
export function getReviewTools(workingDirectory: string) {
  const safeResolve = (filePath: string): string => {
    const absolutePath = resolve(workingDirectory, filePath)
    if (!absolutePath.startsWith(resolve(workingDirectory))) {
      throw new Error(`Path traversal blocked: "${filePath}"`)
    }
    return absolutePath
  }

  const readFileTool = tool(
    async ({ filePath }: { filePath: string }): Promise<string> => {
      const absolutePath = safeResolve(filePath)
      const fileName = absolutePath.split('/').pop() ?? ''
      const extension = '.' + fileName.split('.').pop()

      if (BLOCKED_FILE_NAMES.has(fileName)) {
        return `[BLOCKED] File "${fileName}" is not accessible for security reasons.`
      }
      if (!ALLOWED_EXTENSIONS.has(extension) && !ALLOWED_EXTENSIONS.has(extension.toLowerCase())) {
        return `[BLOCKED] Extension "${extension}" is not in the allowed list.`
      }
      if (!existsSync(absolutePath)) {
        return `[NOT FOUND] "${filePath}" does not exist.`
      }

      const content = readFileSync(absolutePath, 'utf-8')
      const truncated = content.length > MAX_FILE_OUTPUT_CHARS
        ? content.slice(0, MAX_FILE_OUTPUT_CHARS) + '\n... [truncated]'
        : content

      return `// ${filePath}\n${truncated}`
    },
    {
      name: 'read_file',
      description: 'Read the contents of a source file. Provide a path relative to the project root.',
      schema: z.object({ filePath: z.string().describe('Relative path to the file') }),
    }
  )

  const searchCodeTool = tool(
    async ({ pattern, fileGlob }: { pattern: string; fileGlob?: string }): Promise<string> => {
      try {
        const globFlag = fileGlob ? `--include="${fileGlob}"` : ''
        const output = execSync(
          `git grep -n "${pattern}" ${globFlag} -- .`,
          { cwd: workingDirectory, encoding: 'utf-8', timeout: 10_000 }
        )
        const lines = output.trim().split('\n').slice(0, MAX_SEARCH_RESULTS)
        return lines.join('\n') || 'No matches found.'
      } catch {
        return 'No matches found.'
      }
    },
    {
      name: 'search_code',
      description: 'Search the codebase for a pattern using git grep. Returns up to 40 matching lines.',
      schema: z.object({
        pattern: z.string().describe('Search pattern (string or regex)'),
        fileGlob: z.string().optional().describe('Optional file glob, e.g. "*.ts"'),
      }),
    }
  )

  const listDirectoryTool = tool(
    async ({ dirPath }: { dirPath: string }): Promise<string> => {
      const absolutePath = safeResolve(dirPath)
      if (!existsSync(absolutePath)) return `[NOT FOUND] "${dirPath}" does not exist.`

      const entries = readdirSync(absolutePath, { withFileTypes: true })
        .filter((entry) => !entry.name.startsWith('.') && entry.name !== 'node_modules')
        .map((entry) => (entry.isDirectory() ? `${entry.name}/` : entry.name))

      return entries.join('\n') || '(empty directory)'
    },
    {
      name: 'list_directory',
      description: 'List files and subdirectories at a given path.',
      schema: z.object({ dirPath: z.string().describe('Relative path to directory') }),
    }
  )

  const findReferencesTool = tool(
    async ({ symbolName }: { symbolName: string }): Promise<string> => {
      try {
        const output = execSync(
          `git grep -n "\\b${symbolName}\\b" -- .`,
          { cwd: workingDirectory, encoding: 'utf-8', timeout: 10_000 }
        )
        const lines = output.trim().split('\n').slice(0, MAX_SEARCH_RESULTS)
        return lines.join('\n') || 'No references found.'
      } catch {
        return 'No references found.'
      }
    },
    {
      name: 'find_references',
      description: 'Find all references to a symbol (function, class, variable) across the codebase.',
      schema: z.object({ symbolName: z.string().describe('Symbol name to search for') }),
    }
  )

  const gitLogTool = tool(
    async ({ maxCommits }: { maxCommits?: number }): Promise<string> => {
      try {
        const count = Math.min(maxCommits ?? 10, 20)
        const output = execSync(
          `git log --oneline -${count}`,
          { cwd: workingDirectory, encoding: 'utf-8', timeout: 5_000 }
        )
        return output.trim().slice(0, MAX_COMMAND_OUTPUT_CHARS)
      } catch {
        return 'Unable to read git log.'
      }
    },
    {
      name: 'git_log',
      description: 'Show recent git commit history (read-only).',
      schema: z.object({ maxCommits: z.number().optional().describe('Number of commits to show (max 20)') }),
    }
  )

  return [readFileTool, searchCodeTool, listDirectoryTool, findReferencesTool, gitLogTool]
}
