import { spawnSync } from 'node:child_process'
import { writeFileSync, mkdtempSync } from 'node:fs'
import { join, basename } from 'node:path'
import { tmpdir } from 'node:os'
import chalk from 'chalk'
import { select } from '@inquirer/prompts'

export interface EditSession {
  approveAll: boolean
}

export function createEditSession(): EditSession {
  return { approveAll: false }
}

interface IDEInfo {
  label: string
  cli: string
  diffArgs: (orig: string, mod: string) => string[]
}

function detectIDE(): IDEInfo | null {
  const env = process.env
  if (env['CURSOR_TRACE_ID'] || env['CURSOR_SESSION_ID']) {
    return { label: 'Cursor', cli: 'cursor', diffArgs: (o, m) => ['--diff', o, m] }
  }
  if (env['VSCODE_PID'] || env['VSCODE_IPC_HOOK'] || env['VSCODE_CWD']) {
    return { label: 'Visual Studio Code', cli: 'code', diffArgs: (o, m) => ['--diff', o, m] }
  }
  if (env['WINDSURF_ENVIRONMENT'] || env['WINDSURF_SESSION_ID']) {
    return { label: 'Windsurf', cli: 'windsurf', diffArgs: (o, m) => ['--diff', o, m] }
  }
  if (env['INTELLIJ_ENVIRONMENT_READER'] || env['JB_IDE_TYPE'] || env['JETBRAINS_CLIENT_ID']) {
    const cli = (env['JB_IDE_TYPE'] ?? 'idea').toLowerCase()
    return { label: 'JetBrains IDE', cli, diffArgs: (o, m) => ['diff', o, m] }
  }
  return null
}

function tryOpenInIDE(ide: IDEInfo, origPath: string, modPath: string): boolean {
  try {
    const r = spawnSync(ide.cli, ide.diffArgs(origPath, modPath), {
      stdio: 'ignore',
      timeout: 3_000,
      shell: false,
    })
    return r.status === 0
  } catch {
    return false
  }
}

function writeTmp(name: string, content: string): string {
  const dir = mkdtempSync(join(tmpdir(), 'nexarq-'))
  const p = join(dir, name)
  writeFileSync(p, content, 'utf-8')
  return p
}

// Simple line diff — finds removed/added lines and renders them colored
function printDiff(oldContent: string, newContent: string, cols: number): void {
  const oldLines = oldContent.split('\n')
  const newLines = newContent.split('\n')
  const maxDisplay = 50

  // Build a quick diff: walk both line arrays
  const removedIdx = new Set<number>()
  const addedIdx   = new Set<number>()
  let oi = 0
  let ni = 0
  while (oi < oldLines.length || ni < newLines.length) {
    if (oi < oldLines.length && ni < newLines.length && oldLines[oi] === newLines[ni]) {
      oi++; ni++
    } else if (ni < newLines.length && oi + 1 < oldLines.length && oldLines[oi + 1] === newLines[ni]) {
      removedIdx.add(oi++)
    } else if (oi < oldLines.length && ni + 1 < newLines.length && oldLines[oi] === newLines[ni + 1]) {
      addedIdx.add(ni++)
    } else {
      if (oi < oldLines.length)  removedIdx.add(oi++)
      if (ni < newLines.length)  addedIdx.add(ni++)
    }
  }

  let shown = 0
  const maxIdx = Math.max(oldLines.length, newLines.length)
  for (let i = 0; i < maxIdx && shown < maxDisplay; i++) {
    if (removedIdx.has(i)) {
      console.log(chalk.red('  - ' + (oldLines[i] ?? '').slice(0, cols - 6)))
      shown++
    }
    if (addedIdx.has(i)) {
      console.log(chalk.green('  + ' + (newLines[i] ?? '').slice(0, cols - 6)))
      shown++
    }
  }

  if (shown === 0) {
    console.log(chalk.gray('  (binary or whitespace-only change)'))
  }
  if (shown >= maxDisplay) {
    console.log(chalk.gray(`  … diff truncated (${removedIdx.size + addedIdx.size - maxDisplay} more lines)`))
  }
}

/**
 * Shows a Claude Code-style edit approval prompt.
 * Returns 'yes' (apply) or 'no' (skip).
 * Sets session.approveAll when the user chooses "Yes, allow all".
 */
export async function approveEdit(opts: {
  displayPath: string
  oldContent: string
  newContent: string
  session: EditSession
}): Promise<'yes' | 'no'> {
  if (opts.session.approveAll) return 'yes'

  const cols    = Math.max(process.stdout.columns ?? 80, 60)
  const rule    = chalk.gray('─'.repeat(cols))
  const name    = basename(opts.displayPath)

  console.log()
  console.log(chalk.bold(`Update(${opts.displayPath})`))
  console.log()
  console.log(rule)
  printDiff(opts.oldContent, opts.newContent, cols)
  console.log(rule)

  const ide = detectIDE()
  if (ide) {
    const origTmp = writeTmp(`${name}.orig`, opts.oldContent)
    const modTmp  = writeTmp(`${name}.new`,  opts.newContent)
    const opened  = tryOpenInIDE(ide, origTmp, modTmp)
    if (opened) {
      console.log()
      console.log(`  ${chalk.cyan(`Opened changes in ${ide.label} ⧉`)}`)
      console.log()
      console.log(chalk.gray('  Save file to continue…'))
    }
  }

  console.log()

  const choice = await select({
    message: `Do you want to make this edit to ${name}?`,
    choices: [
      { name: 'Yes',                                       value: 'yes',     short: 'Yes'     },
      { name: 'Yes, allow all edits during this session',  value: 'yes-all', short: 'Yes all' },
      { name: 'No',                                        value: 'no',      short: 'No'      },
    ],
    default: 'yes',
  }).catch(() => 'no' as const)

  if (choice === 'yes-all') {
    opts.session.approveAll = true
    return 'yes'
  }
  return choice === 'yes' ? 'yes' : 'no'
}
