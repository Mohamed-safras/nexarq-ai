import { spawnSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { basename } from 'node:path'
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
  gotoArgs: (file: string, line: number) => string[]
}

function detectIDE(): IDEInfo | null {
  const env = process.env
  if (env['CURSOR_TRACE_ID'] || env['CURSOR_SESSION_ID']) {
    return { label: 'Cursor', cli: 'cursor', gotoArgs: (f, l) => ['-g', `${f}:${l}`] }
  }
  if (env['VSCODE_PID'] || env['VSCODE_IPC_HOOK'] || env['VSCODE_CWD']) {
    return { label: 'VS Code', cli: 'code', gotoArgs: (f, l) => ['-g', `${f}:${l}`] }
  }
  if (env['WINDSURF_ENVIRONMENT'] || env['WINDSURF_SESSION_ID']) {
    return { label: 'Windsurf', cli: 'windsurf', gotoArgs: (f, l) => ['-g', `${f}:${l}`] }
  }
  if (env['INTELLIJ_ENVIRONMENT_READER'] || env['JB_IDE_TYPE'] || env['JETBRAINS_CLIENT_ID']) {
    const cli = (env['JB_IDE_TYPE'] ?? 'idea').toLowerCase()
    return { label: 'JetBrains', cli, gotoArgs: (f, l) => ['--line', String(l), f] }
  }
  return null
}

function tryOpenInIDE(ide: IDEInfo, filePath: string, line: number): boolean {
  try {
    const r = spawnSync(ide.cli, ide.gotoArgs(filePath, line), {
      stdio: 'ignore',
      timeout: 3_000,
      shell: process.platform === 'win32',
    })
    return r.status === 0
  } catch {
    return false
  }
}

// Simple line diff — finds removed/added lines and renders them colored
function printDiff(oldContent: string, newContent: string, cols: number): void {
  const oldLines = oldContent.split('\n')
  const newLines = newContent.split('\n')
  const maxDisplay = 50

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

  if (shown === 0) console.log(chalk.gray('  (no visible changes)'))
  if (shown >= maxDisplay) {
    console.log(chalk.gray(`  … diff truncated (${removedIdx.size + addedIdx.size - maxDisplay} more lines)`))
  }
}

/**
 * Shows an edit approval prompt.
 *
 * When fullPath + line are provided and an IDE is detected:
 *   - writes newContent to the real file so the IDE gutter shows the live diff
 *   - opens the file at the changed line in the IDE
 *   - prompts in the terminal to accept or reject
 *   - restores oldContent if rejected
 *
 * Falls back to a terminal-only text diff when no IDE is available.
 */
export async function approveEdit(opts: {
  displayPath: string
  fullPath?: string
  line?: number
  oldContent: string
  newContent: string
  session: EditSession
}): Promise<'yes' | 'no'> {
  if (opts.session.approveAll) return 'yes'

  const cols = Math.max(process.stdout.columns ?? 80, 60)
  const rule = chalk.gray('─'.repeat(cols))
  const name = basename(opts.displayPath)

  console.log()
  console.log(chalk.bold(`Update(${opts.displayPath})`))
  console.log()

  const ide = opts.fullPath ? detectIDE() : null
  let ideOpened = false

  if (ide && opts.fullPath) {
    // Write proposed content to the real file so the IDE gutter shows it live
    writeFileSync(opts.fullPath, opts.newContent, 'utf-8')
    ideOpened = tryOpenInIDE(ide, opts.fullPath, opts.line ?? 1)

    if (ideOpened) {
      console.log(
        `  ${chalk.cyan(`Opened in ${ide.label} ⧉`)}  ` +
        chalk.gray('← gutter shows the suggested change · accept or reject below')
      )
    } else {
      // IDE open failed but we already wrote the file — show inline diff too
      console.log(rule)
      printDiff(opts.oldContent, opts.newContent, cols)
      console.log(rule)
    }
  } else {
    console.log(rule)
    printDiff(opts.oldContent, opts.newContent, cols)
    console.log(rule)
  }

  console.log()

  const choice = await select({
    message: `Apply this fix to ${name}?`,
    choices: [
      { name: 'Yes',                                      value: 'yes',     short: 'Yes'     },
      { name: 'Yes, allow all edits during this session', value: 'yes-all', short: 'Yes all' },
      { name: 'No',                                       value: 'no',      short: 'No'      },
    ],
    default: 'yes',
  }).catch(() => 'no' as const)

  if (choice === 'yes-all') opts.session.approveAll = true

  const accepted = choice === 'yes' || choice === 'yes-all'

  // If we pre-wrote the file, restore on rejection
  if (opts.fullPath && (ideOpened || ide)) {
    if (!accepted) {
      writeFileSync(opts.fullPath, opts.oldContent, 'utf-8')
    }
    // Accepted: file already has the right content — caller must NOT write again
    return accepted ? 'yes' : 'no'
  }

  return accepted ? 'yes' : 'no'
}
