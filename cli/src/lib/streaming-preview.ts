import { writeFileSync, mkdirSync, rmSync } from 'node:fs'
import { dirname, join, basename } from 'node:path'
import { spawn } from 'node:child_process'
import chalk from 'chalk'
import { select } from '@inquirer/prompts'
import { approveEdit, type EditSession } from './edit-approval.ts'

// Preview directory lives at <workingDirectory>/.agent-preview/
const PREVIEW_DIR = '.agent-preview'

// ── IDE detection ─────────────────────────────────────────────────────────────

function detectDiffIDE(): { label: string; cli: string } | null {
  const e = process.env
  if (e['CURSOR_TRACE_ID']       || e['CURSOR_SESSION_ID'])   return { label: 'Cursor',   cli: 'cursor'   }
  if (e['VSCODE_PID']            || e['VSCODE_IPC_HOOK'] || e['VSCODE_CWD']) return { label: 'VS Code', cli: 'code'     }
  if (e['WINDSURF_ENVIRONMENT']  || e['WINDSURF_SESSION_ID']) return { label: 'Windsurf', cli: 'windsurf' }
  return null
}

function spawnDiff(cli: string, original: string, proposed: string): void {
  try {
    const p = spawn(cli, ['--diff', original, proposed], {
      detached: true,
      stdio:    'ignore',
      shell:    process.platform === 'win32',
    })
    p.unref()
  } catch { /* IDE not in PATH */ }
}

// ── Streaming ─────────────────────────────────────────────────────────────────

interface StreamSignal {
  paused:    boolean
  cancelled: boolean
  acceptNow: boolean
}

async function streamContent(
  destPath:   string,
  content:    string,
  onProgress: (written: number, total: number) => void,
  sig:        StreamSignal,
): Promise<void> {
  const total = content.length
  if (!total) { writeFileSync(destPath, '', 'utf-8'); return }

  // Adaptive chunk size: target ~1.8 s of visible streaming, 50–250 chunks
  const chunks  = Math.min(Math.max(50, Math.ceil(total / 60)), 250)
  const chunkSz = Math.ceil(total / chunks)
  const delayMs = Math.max(5, Math.min(28, Math.floor(1800 / chunks)))

  let n = 0
  while (n < total && !sig.cancelled) {
    // Instant-flush when user presses A
    if (sig.acceptNow) { writeFileSync(destPath, content, 'utf-8'); onProgress(total, total); return }

    // Pause loop
    while (sig.paused && !sig.cancelled && !sig.acceptNow) {
      await sleep(50)
    }
    if (sig.cancelled) return
    if (sig.acceptNow) { writeFileSync(destPath, content, 'utf-8'); onProgress(total, total); return }

    n = Math.min(n + chunkSz, total)
    writeFileSync(destPath, content.slice(0, n), 'utf-8')
    onProgress(n, total)

    if (n < total) await sleep(delayMs)
  }
}

const sleep = (ms: number): Promise<void> => new Promise(r => setTimeout(r, ms))

// ── Progress bar ──────────────────────────────────────────────────────────────

function progressBar(n: number, total: number, width = 22): string {
  const filled = total > 0 ? Math.round((n / total) * width) : width
  return '█'.repeat(filled) + '░'.repeat(width - filled)
}

// ── Public API ────────────────────────────────────────────────────────────────

export interface StreamPreviewOptions {
  displayPath:      string   // relative path for display (e.g. "src/auth.ts")
  fullPath:         string   // absolute path to the real file
  oldContent:       string   // original content (empty string for new files)
  newContent:       string   // proposed content to stream
  session:          EditSession
  workingDirectory: string
}

/**
 * Streams `newContent` token-by-token into `.agent-preview/proposed/{displayPath}`,
 * while the IDE shows a live side-by-side diff against the original.
 *
 * Falls back to terminal-only diff when no supported IDE is detected.
 *
 * When the user accepts, writes `newContent` to `fullPath` and returns 'yes'.
 * The caller (write-tools) may write the same content again — that is idempotent.
 */
export async function streamingApproveEdit(opts: StreamPreviewOptions): Promise<'yes' | 'no'> {
  if (opts.session.approveAll) return 'yes'

  const ide  = detectDiffIDE()
  const name = basename(opts.displayPath)

  console.log()
  console.log(chalk.bold(`  Update(${opts.displayPath})`))
  console.log()

  // ── No IDE: terminal-only fallback ────────────────────────────────────────
  if (!ide) {
    return approveEdit({
      displayPath: opts.displayPath,
      oldContent:  opts.oldContent,
      newContent:  opts.newContent,
      session:     opts.session,
    })
  }

  // ── Build preview paths ───────────────────────────────────────────────────
  const base     = join(opts.workingDirectory, PREVIEW_DIR)
  const origPath = join(base, 'original', opts.displayPath)
  const propPath = join(base, 'proposed', opts.displayPath)

  mkdirSync(dirname(origPath), { recursive: true })
  mkdirSync(dirname(propPath), { recursive: true })
  writeFileSync(origPath, opts.oldContent, 'utf-8')
  writeFileSync(propPath, '', 'utf-8')               // empty → IDE right panel starts blank

  // ── Open diff view (non-blocking) ─────────────────────────────────────────
  spawnDiff(ide.cli, origPath, propPath)
  console.log(
    `  ${chalk.cyan(`Opened in ${ide.label} ⧉`)}` +
    chalk.dim('  ·  watch the right panel as code streams in'),
  )
  await sleep(350)                                   // give IDE time to open

  // ── Keyboard capture for streaming controls ───────────────────────────────
  const sig: StreamSignal = { paused: false, cancelled: false, acceptNow: false }
  const wasRaw = process.stdin.isTTY ? process.stdin.isRaw : false

  if (process.stdin.isTTY) {
    process.stdin.setRawMode(true)
    process.stdin.resume()
  }

  const onKey = (raw: Buffer | string): void => {
    const k = raw.toString()
    if      (k === ' ')                    sig.paused    = !sig.paused
    else if (k === 'a' || k === 'A')       sig.acceptNow = true
    else if (k === '\x03' || k === '\x1b') sig.cancelled = true
  }
  if (process.stdin.isTTY) process.stdin.on('data', onKey)

  console.log(
    chalk.gray('  Space') + chalk.dim(' pause  ·  ') +
    chalk.gray('A') + chalk.dim(' accept now  ·  ') +
    chalk.gray('Ctrl+C') + chalk.dim(' reject'),
  )
  process.stdout.write('\n')

  // ── Stream ────────────────────────────────────────────────────────────────
  await streamContent(
    propPath,
    opts.newContent,
    (n, total) => {
      const pct   = total > 0 ? Math.floor((n / total) * 100) : 100
      const state = sig.paused ? chalk.yellow('  ⏸') : ''
      process.stdout.write(
        `\r  ${chalk.dim('Streaming')}  ${chalk.cyan(progressBar(n, total))}  ${chalk.bold(`${pct}%`)}` +
        chalk.dim(`  ${n.toLocaleString()} / ${total.toLocaleString()} chars`) +
        state + '      ',
      )
    },
    sig,
  )

  // ── Restore stdin before prompting ────────────────────────────────────────
  if (process.stdin.isTTY) {
    process.stdin.removeListener('data', onKey)
    try { process.stdin.setRawMode(wasRaw) } catch { /* ignore if already closed */ }
  }

  process.stdout.write('\n\n')

  // ── Cancelled during stream ───────────────────────────────────────────────
  if (sig.cancelled) {
    console.log(chalk.gray('  Rejected.'))
    cleanup(base)
    return 'no'
  }

  // ── Line delta ────────────────────────────────────────────────────────────
  const oldLineCount = opts.oldContent ? opts.oldContent.split('\n').length : 0
  const newLineCount = opts.newContent.split('\n').length
  const delta        = newLineCount - oldLineCount
  if (delta !== 0) {
    process.stdout.write(
      chalk.dim('  ') +
      (delta > 0 ? chalk.green(`+${Math.abs(delta)} lines`) : chalk.red(`-${Math.abs(delta)} lines`)) +
      chalk.dim(`  (${newLineCount} total)\n\n`),
    )
  }

  // ── Final accept / reject prompt ──────────────────────────────────────────
  const choice = await select({
    message: `Apply changes to ${name}?`,
    choices: [
      { name: chalk.green('✓') + '  Yes  — apply changes',                    value: 'yes',     short: 'Yes'     },
      { name: chalk.cyan('⟳') + '  Yes, allow all edits in this session',     value: 'yes-all', short: 'Yes all' },
      { name: chalk.gray('·') + '  No   — discard preview',                   value: 'no',      short: 'No'      },
    ],
    default: 'yes',
  }).catch(() => 'no' as const)

  if (choice === 'yes-all') opts.session.approveAll = true
  const accepted = choice === 'yes' || choice === 'yes-all'

  cleanup(base)

  // Write to real file on acceptance (write-tools will write again — idempotent)
  if (accepted) writeFileSync(opts.fullPath, opts.newContent, 'utf-8')

  return accepted ? 'yes' : 'no'
}

function cleanup(base: string): void {
  try { rmSync(base, { recursive: true, force: true }) } catch { /* ignore */ }
}
