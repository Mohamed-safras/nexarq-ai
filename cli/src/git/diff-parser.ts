import type { DiffResult, FileDiff } from '@nexarq/common/interfaces'
import type { ChangeType } from '@nexarq/common/types'

// ── Language detection ────────────────────────────────────────────────────────

const EXT_LANG: Record<string, string> = {
  ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript',
  py: 'python', rb: 'ruby', go: 'go', rs: 'rust', java: 'java',
  cs: 'csharp', cpp: 'cpp', c: 'c', h: 'c', hpp: 'cpp',
  php: 'php', swift: 'swift', kt: 'kotlin', scala: 'scala',
  sh: 'bash', bash: 'bash', zsh: 'bash',
  sql: 'sql', graphql: 'graphql', gql: 'graphql',
  tf: 'terraform', hcl: 'hcl',
  yaml: 'yaml', yml: 'yaml', json: 'json', toml: 'toml',
  md: 'markdown', html: 'html', css: 'css', scss: 'css', sass: 'css',
  dockerfile: 'docker',
}

function langFromPath(filePath: string): string {
  const lower = filePath.toLowerCase()
  if (lower.endsWith('dockerfile') || lower.includes('/dockerfile')) return 'docker'
  const ext = lower.split('.').pop() ?? ''
  return EXT_LANG[ext] ?? 'unknown'
}

// ── Change-type inference ─────────────────────────────────────────────────────

function inferChangeType(
  files: FileDiff[],
  rawDiff: string,
): ChangeType {
  const paths   = files.map((f) => f.path.toLowerCase())
  const content = rawDiff.toLowerCase()

  if (paths.some((p) => /\.(test|spec)\.|__tests__|\/test\/|\/tests\//.test(p)))
    return 'test'
  if (paths.some((p) => /(migration|schema|\.sql$)/.test(p)))
    return 'database'
  if (paths.some((p) => /(dockerfile|\.github|\/ci\/|\.tf$|k8s|helm)/.test(p)))
    return 'general' // devops — no dedicated ChangeType yet, keep general
  if (paths.some((p) => /(readme|docs?\/|\.md$)/.test(p)) && files.length < 5)
    return 'docs'
  if (paths.some((p) => /(auth|password|crypto|token|secret|cert)/.test(p)))
    return 'security'
  if (content.includes('performance') || content.includes('optimize') || content.includes('cache'))
    return 'performance'
  if (content.includes('fix') || content.includes('bug') || content.includes('error'))
    return 'bugfix'
  if (content.includes('refactor') || content.includes('rename') || content.includes('move'))
    return 'refactor'

  // Default to feature for new files or pure additions
  const hasNewFiles = files.some((f) => f.isNewFile)
  const totalAdded  = files.reduce((s, f) => s + f.addedLines.length, 0)
  const totalRemoved = files.reduce((s, f) => s + f.removedLines.length, 0)
  if (hasNewFiles || totalAdded > totalRemoved * 3) return 'feature'

  return 'general'
}

// ── Primary language ──────────────────────────────────────────────────────────

function primaryLanguage(files: FileDiff[]): string {
  const counts = new Map<string, number>()
  for (const f of files) {
    if (f.language === 'unknown') continue
    const lines = f.addedLines.length + f.removedLines.length
    counts.set(f.language, (counts.get(f.language) ?? 0) + lines)
  }
  let best = 'unknown', bestCount = 0
  for (const [lang, count] of counts) {
    if (count > bestCount) { best = lang; bestCount = count }
  }
  return best
}

// ── Git diff parser ───────────────────────────────────────────────────────────

export function parseDiff(rawDiff: string): DiffResult {
  const files: FileDiff[] = []
  let currentFile: FileDiff | null = null

  for (const line of rawDiff.split('\n')) {
    // Start of a new file section
    if (line.startsWith('diff --git ')) {
      if (currentFile) files.push(currentFile)
      // Extract path from "diff --git a/foo b/foo"
      const match = line.match(/^diff --git a\/.+ b\/(.+)$/)
      const filePath = match?.[1] ?? line.split(' ').pop() ?? 'unknown'
      currentFile = {
        path:        filePath,
        language:    langFromPath(filePath),
        addedLines:  [],
        removedLines: [],
        content:     '',
        isNewFile:   false,
        isDeleted:   false,
        isBinary:    false,
      }
      continue
    }

    if (!currentFile) continue

    if (line.startsWith('new file mode'))     { currentFile.isNewFile = true;  continue }
    if (line.startsWith('deleted file mode')) { currentFile.isDeleted = true;  continue }
    if (line.startsWith('Binary files'))      { currentFile.isBinary  = true;  continue }
    if (line.startsWith('--- ') || line.startsWith('+++ ') || line.startsWith('@@')) continue
    if (line.startsWith('index '))            continue

    if (line.startsWith('+') && !line.startsWith('+++')) {
      currentFile.addedLines.push(line.slice(1))
    } else if (line.startsWith('-') && !line.startsWith('---')) {
      currentFile.removedLines.push(line.slice(1))
    }
    currentFile.content += line + '\n'
  }

  if (currentFile) files.push(currentFile)

  const totalAdded   = files.reduce((s, f) => s + f.addedLines.length, 0)
  const totalRemoved = files.reduce((s, f) => s + f.removedLines.length, 0)
  const changeType   = inferChangeType(files, rawDiff)
  const lang         = primaryLanguage(files)

  return {
    files,
    rawDiff,
    totalAdded,
    totalRemoved,
    changeType,
    repoType:        'git',
    primaryLanguage: lang,
  }
}
