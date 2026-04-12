import type { NexarqTheme, ThemeVariant } from './theme.ts'
import { THEME_LABELS, getThemeByVariant } from './theme.ts'

// ── Full NEXARQ ASCII logo (6 lines) ─────────────────────────────────────────
const LOGO_LINES = [
  '  ██╗  ██╗███████╗██╗  ██╗ █████╗ ██████╗  ██████╗',
  '  ████╗ ██║██╔════╝╚██╗██╔╝██╔══██╗██╔══██╗██╔═══██╗',
  '  ██╔██╗██║█████╗   ╚███╔╝ ███████║██████╔╝██║   ██║',
  '  ██║╚██╗██║██╔══╝   ██╔██╗██╔══██║██╔══██╗██║▄▄ ██║',
  '  ██║ ╚████║███████╗██╔╝ ██╗██║  ██║██║  ██║╚██████╔╝',
  '  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚══▀▀═╝',
]

// ── ANSI color helpers ────────────────────────────────────────────────────────
function ansiFg(hex: string): string {
  const R = parseInt(hex.slice(1, 3), 16)
  const G = parseInt(hex.slice(3, 5), 16)
  const B = parseInt(hex.slice(5, 7), 16)
  return `\x1b[38;2;${R};${G};${B}m`
}

const R = '\x1b[0m' // reset

// Lerp between two hex colors across `steps` rows, returning one ANSI escape per row
function logoGradient(from: string, to: string, steps: number): string[] {
  const fr = parseInt(from.slice(1, 3), 16)
  const fg = parseInt(from.slice(3, 5), 16)
  const fb = parseInt(from.slice(5, 7), 16)
  const tr = parseInt(to.slice(1, 3), 16)
  const tg = parseInt(to.slice(3, 5), 16)
  const tb = parseInt(to.slice(5, 7), 16)
  return Array.from({ length: steps }, (_, i) => {
    const t = steps === 1 ? 0 : i / (steps - 1)
    const r = Math.round(fr + (tr - fr) * t)
    const g = Math.round(fg + (tg - fg) * t)
    const b = Math.round(fb + (tb - fb) * t)
    return `\x1b[38;2;${r};${g};${b}m`
  })
}

// ── Build diff lines with ANSI colors from a theme ──────────────────────────
function buildDiffPreview(theme: NexarqTheme): string[] {
  const add = (text: string) => ansiFg(theme.green) + text + R
  const del = (text: string) => ansiFg(theme.red) + text + R

  return [
    del('- console.log("Hello World")'),
    add('+ console.log("Hello Nexarq")'),
  ]
}

// ── Shared header printed above every step (logo + description) ──────────────
// Layout: blank(1) + logo(6) + tagline(1) + blank(1) + started(1) + blank(1) = 11 lines
export const HEADER_LINE_COUNT = 11

export function printHeader(theme: NexarqTheme): void {
  const logoColors = logoGradient(theme.cyan, theme.purple, LOGO_LINES.length)
  const write = (text = '') => process.stdout.write('\x1b[2K' + text + '\n')

  write()
  for (let i = 0; i < LOGO_LINES.length; i++) {
    write((logoColors[i] ?? '') + LOGO_LINES[i] + R)
  }
  write(ansiFg(theme.fgDim) + '  multi-agent code review and coder assistant powered by AI' + R)
  write()
  write('  Let\'s get started.')
  write()
}

// ── Erase N lines above cursor and reposition to where they started ──────────
function eraseLines(n: number): void {
  if (n <= 0) return
  process.stdout.write(`\x1b[${n}A`) // move up n lines
  process.stdout.write('\x1b[J')      // erase from cursor to end of screen
}

// ── Interactive theme picker ──────────────────────────────────────────────────
// Frame layout:
//   header(11) + choose(1) + later(1) + blank(1)       = 14  (PICKER_HEADER)
//   + instruction(1) + blank(1) + list(6) + blank(1) + diff(2) + blank(1) + controls(1) = 13
//   Total = 27 lines
// Uses \x1b[nA (move up) + \x1b[J (erase to end) — no full-screen clear needed.
async function interactiveThemeSelect(initial: ThemeVariant): Promise<ThemeVariant> {
  const variants = Object.keys(THEME_LABELS) as ThemeVariant[]
  let index = variants.indexOf(initial)
  let selected = false
  let firstFrame = true

  const PICKER_HEADER = HEADER_LINE_COUNT + 3  // +choose +later +blank = 14
  const PICKER_LINES = 1 + 1 + variants.length + 1 + 2 + 1 + 1  // 13
  const FRAME_LINES = PICKER_HEADER + PICKER_LINES               // 27

  const writeLine = (text = '') => process.stdout.write('\x1b[2K' + text + '\n')

  while (!selected) {
    const variant = variants[index]!
    const theme = getThemeByVariant(variant)
    const diffLines = buildDiffPreview(theme)

    if (!firstFrame) {
      process.stdout.write(`\x1b[${FRAME_LINES}A\x1b[J`)
    }
    firstFrame = false

    // ── Header (shared with init steps) ──────────────────────────────────────
    printHeader(theme)

    // ── Picker-specific header lines ──────────────────────────────────────────
    writeLine('  Step 1 · Choose the text style that looks best with your terminal')
    writeLine(ansiFg(theme.fgDim) + '  To change this later, run: nexarq config --theme' + R)
    writeLine()

    // ── Interactive list ──────────────────────────────────────────────────────
    writeLine('  Navigate with ↑↓ · Enter to select · Esc to cancel')
    writeLine()

    for (let i = 0; i < variants.length; i++) {
      const v = variants[i]!
      const label = '  ' + THEME_LABELS[v]
      if (i === index) {
        writeLine(ansiFg(theme.cyan) + '  ▶ ' + label + R + '   ' + ansiFg(theme.fgDim) + '← selected' + R)
      } else {
        writeLine('    ' + label)
      }
    }

    writeLine()
    for (const line of diffLines) {
      writeLine('  ' + line)
    }
    writeLine()
    writeLine(ansiFg(theme.fgDim) + '  ↑↓ navigate list · Enter to confirm' + R)

    const key = await readKey()

    if (key === 'up') {
      index = (index - 1 + variants.length) % variants.length
    } else if (key === 'down') {
      index = (index + 1) % variants.length
    } else if (key === 'enter') {
      selected = true
      // Erase picker frame, leave only the shared header for the next step
      eraseLines(FRAME_LINES)
      const theme = getThemeByVariant(variants[index]!)
      printHeader(theme)
    } else if (key === 'esc') {
      throw new Error('cancelled')
    }
  }

  return variants[index]!
}

// ── Read one keypress (cross-platform) ───────────────────────────────────────
function readKey(): Promise<string> {
  return new Promise((resolve) => {
    const buf = Buffer.alloc(3)
    let offset = 0

    const onData = (chunk: Buffer) => {
      for (let i = 0; i < chunk.length && offset < 3; i++) {
        const byte = chunk[i]
        if (byte !== undefined) {
          buf[offset] = byte
          offset++
        }
      }

      if (offset === 1 && buf[0] === 0x1b) {
        setTimeout(() => {
          if (offset === 1 && buf[0] === 0x1b) {
            cleanup()
            resolve('esc')
          }
        }, 30)
        return
      }

      if (offset === 3) {
        if (buf[0] === 0x1b && buf[1] === 0x5b && buf[2] === 0x41) { cleanup(); resolve('up') }
        else if (buf[0] === 0x1b && buf[1] === 0x5b && buf[2] === 0x42) { cleanup(); resolve('down') }
        else { offset = 0 }
      }
      else if (offset === 1 && (buf[0] === 0x0d || buf[0] === 0x0a)) {
        cleanup(); resolve('enter')
      }
      else if (offset === 1 && buf[0] === 0x03) {
        cleanup(); resolve('esc')
      }
    }

    const cleanup = () => {
      process.stdin.removeListener('data', onData)
      process.stdin.setRawMode(false)
      process.stdin.resume()
    }

    process.stdin.resume()
    process.stdin.setRawMode(true)
    process.stdin.on('data', onData)
  })
}

/**
 * runWelcomeScreen
 *
 * Interactive theme picker with live logo + diff preview.
 * On confirm, erases the picker and leaves only the shared header on screen.
 * Returns the chosen ThemeVariant.
 */
export async function runWelcomeScreen(): Promise<ThemeVariant> {
  return interactiveThemeSelect('dark')
}
