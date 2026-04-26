import { existsSync, writeFileSync, readFileSync, chmodSync, mkdirSync } from 'fs'
import { join } from 'path'
import { execSync } from 'child_process'

const NEXARQ_MARKER = '# nexarq-managed'

// The hook resolves nexarq at runtime so it works whether installed globally
// or run via bun in the repo that owns the CLI.
const POST_COMMIT_SCRIPT = `#!/bin/sh
${NEXARQ_MARKER}
[ "$NEXARQ_SKIP" = "1" ] && exit 0

# Resolve nexarq: prefer global binary, fall back to bun in the nexarq repo
if command -v nexarq >/dev/null 2>&1; then
  nexarq run --hook
elif [ -n "$NEXARQ_BUN_PATH" ] && [ -n "$NEXARQ_CLI_PATH" ]; then
  "$NEXARQ_BUN_PATH" run "$NEXARQ_CLI_PATH/src/index.ts" run --hook
else
  echo "nexarq: not found. Run 'nexarq hook install post-commit' from the nexarq-ai/cli directory or install globally." >&2
fi
`

const PRE_PUSH_SCRIPT = `#!/bin/sh
${NEXARQ_MARKER}
[ "$NEXARQ_SKIP" = "1" ] && exit 0

if command -v nexarq >/dev/null 2>&1; then
  nexarq run --pre-push
elif [ -n "$NEXARQ_BUN_PATH" ] && [ -n "$NEXARQ_CLI_PATH" ]; then
  "$NEXARQ_BUN_PATH" run "$NEXARQ_CLI_PATH/src/index.ts" run --pre-push
else
  echo "nexarq: not found. Install globally with: cd nexarq-ai/cli && bun run build && bun link" >&2
fi
`

function getGitHooksDir(): string {
  try {
    const gitDir = execSync('git rev-parse --git-dir', { encoding: 'utf-8' }).trim()
    return join(gitDir, 'hooks')
  } catch {
    throw new Error('Not inside a git repository')
  }
}

/** Returns the path to the CLI source dir (where this file lives, two levels up) */
function getCliSourceDir(): string {
  // __dirname → cli/src/git  →  go up two levels to cli/
  return join(new URL(import.meta.url).pathname.replace(/^\/([A-Z]:)/, '$1'), '..', '..', '..')
}

function getBunPath(): string {
  const cmds = process.platform === 'win32'
    ? ['where.exe bun']
    : ['which bun', 'command -v bun']
  for (const cmd of cmds) {
    try {
      const found = execSync(cmd, { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }).trim().split('\n')[0]
      if (found) return found
    } catch { /* try next */ }
  }
  return 'bun'
}

export async function installHook(hookType: 'post-commit' | 'pre-push'): Promise<void> {
  const hooksDir = getGitHooksDir()
  mkdirSync(hooksDir, { recursive: true })

  const hookPath   = join(hooksDir, hookType)
  const bunPath    = getBunPath()
  const cliSrcDir  = getCliSourceDir()

  // Embed bun + CLI paths so the hook works without a global install
  let hookScript = hookType === 'post-commit' ? POST_COMMIT_SCRIPT : PRE_PUSH_SCRIPT
  hookScript = hookScript
    .replace('${NEXARQ_BUN_PATH}', bunPath)
    .replace('${NEXARQ_CLI_PATH}', cliSrcDir)

  // Also set the env vars inline in the script
  const envBlock = `NEXARQ_BUN_PATH="${bunPath}"\nNEXARQ_CLI_PATH="${cliSrcDir}"\n`
  hookScript = hookScript.replace(
    `${NEXARQ_MARKER}\n`,
    `${NEXARQ_MARKER}\n${envBlock}`
  )

  if (existsSync(hookPath)) {
    const existingContent = readFileSync(hookPath, 'utf-8')
    if (!existingContent.includes(NEXARQ_MARKER)) {
      // Back up any pre-existing non-nexarq hook
      writeFileSync(`${hookPath}.backup`, existingContent, 'utf-8')
    }
  }

  writeFileSync(hookPath, hookScript, 'utf-8')
  chmodSync(hookPath, 0o755)
}

export async function uninstallHook(hookType: 'post-commit' | 'pre-push'): Promise<void> {
  const hooksDir = getGitHooksDir()
  const hookPath = join(hooksDir, hookType)

  if (!existsSync(hookPath)) return

  const content = readFileSync(hookPath, 'utf-8')
  if (!content.includes(NEXARQ_MARKER)) return

  const backupPath = `${hookPath}.backup`
  if (existsSync(backupPath)) {
    const backupContent = readFileSync(backupPath, 'utf-8')
    writeFileSync(hookPath, backupContent, 'utf-8')
  } else {
    const { unlinkSync } = await import('fs')
    unlinkSync(hookPath)
  }
}

export async function getHookStatus(): Promise<Record<string, boolean>> {
  let hooksDir: string
  try {
    hooksDir = getGitHooksDir()
  } catch {
    return { 'post-commit': false, 'pre-push': false }
  }

  return Object.fromEntries(
    ['post-commit', 'pre-push'].map((hookType) => {
      const hookPath = join(hooksDir, hookType)
      if (!existsSync(hookPath)) return [hookType, false]
      const content = readFileSync(hookPath, 'utf-8')
      return [hookType, content.includes(NEXARQ_MARKER)]
    })
  )
}
