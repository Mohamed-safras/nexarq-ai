import { tool } from '@langchain/core/tools'
import { z } from 'zod'
import { readFileSync, readdirSync, existsSync } from 'fs'
import { join, resolve, relative } from 'path'
import { execSync } from 'child_process'
import { BLOCKED_FILE_NAMES, ALLOWED_EXTENSIONS } from '@nexarq/common/constants'

const MAX_FILE_OUTPUT_CHARS = 8_000
const MAX_SEARCH_RESULTS    = 40
const MAX_COMMAND_OUTPUT_CHARS = 6_000

/**
 * Read-only tools available to ALL agents (review + coding).
 * These never modify the filesystem or execute arbitrary code.
 */
export function getReadTools(workingDirectory: string) {
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
      const fileName  = absolutePath.split('/').pop() ?? ''
      const extension = '.' + fileName.split('.').pop()

      if (BLOCKED_FILE_NAMES.has(fileName)) {
        return `[BLOCKED] File "${fileName}" is not accessible for security reasons.`
      }
      if (!ALLOWED_EXTENSIONS.has(extension) && !ALLOWED_EXTENSIONS.has(extension.toLowerCase())) {
        return `[BLOCKED] Extension "${extension}" is not in the allowed list.`
      }
      if (!existsSync(absolutePath)) return `[NOT FOUND] "${filePath}" does not exist.`

      const content   = readFileSync(absolutePath, 'utf-8')
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
        const output   = execSync(
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
        pattern:  z.string().describe('Search pattern (string or regex)'),
        fileGlob: z.string().optional().describe('Optional file glob, e.g. "*.ts"'),
      }),
    }
  )

  const listDirectoryTool = tool(
    async ({ dirPath }: { dirPath: string }): Promise<string> => {
      const absolutePath = safeResolve(dirPath)
      if (!existsSync(absolutePath)) return `[NOT FOUND] "${dirPath}" does not exist.`

      const entries = readdirSync(absolutePath, { withFileTypes: true })
        .filter((e) => !e.name.startsWith('.') && e.name !== 'node_modules')
        .map((e) => (e.isDirectory() ? `${e.name}/` : e.name))

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
        const count  = Math.min(maxCommits ?? 10, 20)
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

  const gitDiffTool = tool(
    async ({ target }: { target?: string }): Promise<string> => {
      try {
        const output = execSync(`git diff ${target ?? 'HEAD'}`, {
          cwd: workingDirectory, encoding: 'utf-8', timeout: 5_000,
        })
        return output.trim() || '(no changes)'
      } catch {
        return 'Unable to read git diff.'
      }
    },
    {
      name: 'git_diff',
      description: 'Show the current working-tree diff against HEAD or another ref.',
      schema: z.object({ target: z.string().optional().describe('Git ref to diff against (default: HEAD)') }),
    }
  )

  const gitStatusTool = tool(
    async (): Promise<string> => {
      try {
        const output = execSync('git status --short', {
          cwd: workingDirectory, encoding: 'utf-8', timeout: 5_000,
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

  const webSearchTool = tool(
    async ({ query }: { query: string }): Promise<string> => {
      const apiKey = process.env['NEXARQ_BRAVE_API_KEY']
      if (!apiKey) {
        return '[WEB SEARCH UNAVAILABLE] Set NEXARQ_BRAVE_API_KEY to enable web search for CVE lookups and documentation.'
      }
      try {
        const url = `https://api.search.brave.com/res/v1/web/search?q=${encodeURIComponent(query)}&count=5`
        const res = await fetch(url, {
          headers: { 'X-Subscription-Token': apiKey, 'Accept': 'application/json' },
          signal: AbortSignal.timeout(10_000),
        })
        if (!res.ok) return `[WEB SEARCH ERROR] HTTP ${res.status}`

        type BraveResult = { title: string; url: string; description?: string }
        type BraveResponse = { web?: { results?: BraveResult[] } }
        const data = await res.json() as BraveResponse
        const results = data.web?.results ?? []
        if (results.length === 0) return 'No results found.'

        return results
          .map((r, i) => `${i + 1}. ${r.title}\n   ${r.url}\n   ${r.description ?? ''}`)
          .join('\n\n')
      } catch (err) {
        return `[WEB SEARCH ERROR] ${err instanceof Error ? err.message : String(err)}`
      }
    },
    {
      name: 'web_search',
      description: 'Search the web for CVEs, security advisories, library docs, or changelogs. Best for looking up known vulnerabilities by name or package.',
      schema: z.object({ query: z.string().describe('Search query, e.g. "CVE-2024-1234" or "express CORS vulnerability"') }),
    }
  )

  return [readFileTool, searchCodeTool, listDirectoryTool, findReferencesTool, gitLogTool, gitDiffTool, gitStatusTool, webSearchTool]
}
