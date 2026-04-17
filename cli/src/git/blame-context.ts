import { execSync } from 'node:child_process'

export interface BlameContext {
  /** Lines added in the diff that belong to the current author */
  authorLines: number
  /** Lines that existed before this diff (inherited debt) */
  inheritedLines: number
  /** Git author email of the current committer */
  authorEmail: string
  /** Summary sentence injected into agent prompts */
  summary: string
}

/**
 * Extracts blame context from the current diff.
 * Agents use this to distinguish new issues (author's) from pre-existing ones.
 *
 * Cost: zero tokens — this runs git locally, no LLM call.
 */
export function getBlameContext(workingDirectory: string): BlameContext | null {
  try {
    const authorEmail = execSync('git config user.email', {
      cwd: workingDirectory,
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'ignore'],
    }).trim()

    const diffStat = execSync('git diff HEAD~1 HEAD --numstat 2>/dev/null || git diff --cached --numstat', {
      cwd: workingDirectory,
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'ignore'],
    }).trim()

    let authorLines = 0
    for (const line of diffStat.split('\n')) {
      const parts = line.split('\t')
      if (parts.length >= 2) {
        const added = parseInt(parts[0] ?? '0', 10)
        if (!isNaN(added)) authorLines += added
      }
    }

    // Count pre-existing lines in changed files via blame
    const changedFiles = execSync(
      'git diff HEAD~1 HEAD --name-only 2>/dev/null || git diff --cached --name-only',
      { cwd: workingDirectory, encoding: 'utf-8', stdio: ['pipe', 'pipe', 'ignore'] }
    ).trim().split('\n').filter(Boolean).slice(0, 10) // cap at 10 files for speed

    let inheritedLines = 0
    for (const file of changedFiles) {
      try {
        const blameOutput = execSync(`git blame --line-porcelain "${file}" 2>/dev/null`, {
          cwd: workingDirectory,
          encoding: 'utf-8',
          stdio: ['pipe', 'pipe', 'ignore'],
          timeout: 3000,
        })
        const authorMatches = blameOutput.match(/^author-mail <([^>]+)>/gm) ?? []
        const fileInherited = authorMatches.filter(
          (line) => !line.includes(authorEmail)
        ).length
        inheritedLines += fileInherited
      } catch {
        // blame can fail on new files — skip
      }
    }

    const summary = authorLines > 0
      ? `This diff adds ${authorLines} lines by ${authorEmail}. ` +
        `Focus your review on the new lines — ${inheritedLines} pre-existing lines from other authors are present but lower priority.`
      : `Reviewing changes in working directory.`

    return { authorEmail, authorLines, inheritedLines, summary }
  } catch {
    return null
  }
}

/**
 * Parses @file mentions from user input, e.g.
 *   "nexarq run @src/auth.ts @src/routes/users.ts"
 * Returns the list of file paths to append as extra context.
 */
export function parseFileMentions(input: string): string[] {
  return [...input.matchAll(/@([\w./\-]+)/g)]
    .map((match) => match[1])
    .filter((path): path is string => Boolean(path))
}

/**
 * Reads @file mentions from disk and returns their content as a context block.
 * Token-safe: truncates each file to 200 lines.
 */
export async function buildFileMentionContext(
  filePaths: string[],
  workingDirectory: string
): Promise<string> {
  if (filePaths.length === 0) return ''

  const { existsSync, readFileSync } = await import('node:fs')
  const { join } = await import('node:path')

  const blocks: string[] = []
  for (const filePath of filePaths.slice(0, 5)) { // max 5 files
    const fullPath = join(workingDirectory, filePath)
    if (!existsSync(fullPath)) continue
    try {
      const lines = readFileSync(fullPath, 'utf-8').split('\n')
      const truncated = lines.slice(0, 200).join('\n')
      const note = lines.length > 200 ? `\n[...${lines.length - 200} lines truncated]` : ''
      blocks.push(`\`\`\`\n// @${filePath}\n${truncated}${note}\n\`\`\``)
    } catch { /* skip unreadable files */ }
  }

  return blocks.length > 0 ? `\n\n--- PINNED FILES ---\n${blocks.join('\n\n')}\n--- END PINNED FILES ---` : ''
}
