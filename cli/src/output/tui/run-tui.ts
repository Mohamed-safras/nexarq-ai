import type { RunSummary } from '@nexarq/common/interfaces'
import { loadConfig } from '../../config/config-loader.ts'
import { getThemeByVariant, themeToAnsi } from './theme.ts'

export type AgentStatus = 'pending' | 'running' | 'done' | 'error'

export interface RunTUI {
  initAgents(names: string[]): void
  setAgentStatus(name: string, status: AgentStatus): void
  appendChunk(agentName: string, text: string): void
  addFinding(agentName: string, severity: string, lines: string[], latencyMs?: number): void
  updateFooter(agentsRun: number, total: number, summary: Partial<RunSummary>, tokens: number): void
  showComplete(durationMs: number): void
  waitForExit(): Promise<void>
  destroy(): void
}

// ── Fixed ANSI codes (non-theme) ──────────────────────────────────────────────
const R    = '\x1b[0m'
const BOLD = '\x1b[1m'
const DIM2 = '\x1b[2m'   // terminal-native dim (used for separators/rules)

const ENTER_ALT  = '\x1b[?1049h\x1b[?25l'
const EXIT_ALT   = '\x1b[?25h\x1b[?1049l'
const HOME_ERASE = '\x1b[H\x1b[J'

const ICON: Record<AgentStatus, string>  = { pending:'·', running:'●', done:'✓', error:'✗' }

// eslint-disable-next-line no-control-regex
const ANSI_RE = /\x1b\[[0-9;]*m/g
function vis(s: string): number { return s.replace(ANSI_RE, '').length }
function padR(s: string, w: number): string { return s + ' '.repeat(Math.max(0, w - vis(s))) }

/**
 * Word-wrap PLAIN text (no ANSI codes) at word boundaries.
 * Returns indented segments — colorize AFTER wrapping, never before.
 */
function wrapPlain(plain: string, maxCols: number, indent: string): string[] {
  const text = plain.trimEnd()
  if (text.length === 0) return [indent]
  if (text.length <= maxCols) return [indent + text]

  const out: string[] = []
  const words = text.split(' ')
  let line = indent

  for (const word of words) {
    const candidate = line === indent ? indent + word : line + ' ' + word
    if (candidate.length - indent.length <= maxCols) {
      line = candidate
    } else {
      if (line !== indent) out.push(line)
      // Word longer than column: hard-break it
      if (word.length > maxCols) {
        for (let i = 0; i < word.length; i += maxCols) {
          out.push(indent + word.slice(i, i + maxCols))
        }
        line = indent
      } else {
        line = indent + word
      }
    }
  }
  if (line !== indent) out.push(line)
  return out.length > 0 ? out : [indent]
}

// ── State ─────────────────────────────────────────────────────────────────────
interface AgentRow { name: string; status: AgentStatus }
interface Finding  { agentName: string; severity: string; lines: string[] }

export async function createRunTUI(diffLineCount: number): Promise<RunTUI> {
  // ── Load theme from config ──────────────────────────────────────────────────
  const config  = await loadConfig()
  const variant = config.theme ?? 'dark'
  const theme   = getThemeByVariant(variant)
  const C       = themeToAnsi(theme)

  const AGENT_COLOR: Record<AgentStatus, string> = {
    pending: C.dim,
    running: C.cyan,
    done:    C.green,
    error:   C.red,
  }

  function sevColor(s: string): string {
    switch (s.toLowerCase()) {
      case 'critical': return C.critical + BOLD
      case 'high':     return C.high
      case 'medium':   return C.medium
      case 'low':      return C.low
      case 'info':     return C.info
      default:         return C.dim
    }
  }

  // ── Tokenizer-based syntax highlighter ────────────────────────────────────
  const KW = new Set([
    'const','let','var','function','class','interface','type','enum',
    'async','await','return','if','else','for','while','do','switch',
    'case','break','continue','new','delete','typeof','instanceof',
    'import','export','from','default','extends','implements',
    'public','private','protected','readonly','static','abstract',
    'override','try','catch','finally','throw','yield','in','of','as',
    'true','false','null','undefined','void','never','any','unknown',
  ])

  type Token = { re: RegExp; fn: (m: string) => string }
  const TOKENS: Token[] = [
    // Line comment
    { re: /^\/\/.*/,                    fn: m => C.dim + m + R },
    // Block comment (single-line portion)
    { re: /^\/\*.*?\*\//,              fn: m => C.dim + m + R },
    // Template literal
    { re: /^`(?:[^`\\]|\\.)*`/,       fn: m => C.yellow + m + R },
    // Double-quoted string
    { re: /^"(?:[^"\\]|\\.)*"/,       fn: m => C.green + m + R },
    // Single-quoted string
    { re: /^'(?:[^'\\]|\\.)*'/,       fn: m => C.green + m + R },
    // Number
    { re: /^(?:0x[\da-f]+|0b[01]+|\d+(?:\.\d+)?(?:e[+-]?\d+)?)\b/i,
                                        fn: m => C.orange + m + R },
    // Identifier → keyword or type or plain
    { re: /^[a-zA-Z_$][\w$]*/,        fn: m => {
        if (KW.has(m))                    return C.purple + BOLD + m + R
        if (/^[A-Z]/.test(m))            return C.cyan + m + R   // PascalCase = type
        return m
    }},
    // Operator
    { re: /^(?:===|!==|=>|[+\-*/%=<>!&|^~?:]+)/, fn: m => C.yellow + m + R },
    // Punctuation
    { re: /^[(){}[\];,.]/, fn: m => C.dim + m + R },
    // Whitespace / fallthrough
    { re: /^[\s\S]/,        fn: m => m },
  ]

  function highlightCode(plain: string): string {
    let result = ''
    let rest   = plain
    while (rest.length > 0) {
      let hit = false
      for (const { re, fn } of TOKENS) {
        const m = rest.match(re)
        if (m?.[0]) { result += fn(m[0]); rest = rest.slice(m[0].length); hit = true; break }
      }
      if (!hit) { result += rest[0]; rest = rest.slice(1) }
    }
    return result
  }

  // ── Prose / markdown colorizer (outside code blocks) ─────────────────────
  function colorizeProse(line: string): string {
    const t = line.trimStart()

    // Diff lines
    if (t.startsWith('+++ ') || t.startsWith('--- ')) return C.dim + line + R
    if (t.startsWith('+'))   return C.green + line + R
    if (t.startsWith('-'))   return C.red   + line + R
    if (t.startsWith('@@'))  return C.cyan + DIM2 + line + R
    if (t.startsWith('diff --git')) return C.dim + line + R

    // Markdown headings
    if (/^#{1,3} /.test(t)) return BOLD + C.cyan + line + R

    // Severity keywords (replace inline, don't ANSI-wrap the whole line)
    const replaced = line
      .replace(/\bCRITICAL\b/g,   `${C.critical}${BOLD}CRITICAL${R}`)
      .replace(/\bHIGH\b/g,       `${C.high}HIGH${R}`)
      .replace(/\bMEDIUM\b/g,     `${C.medium}MEDIUM${R}`)
      .replace(/\bWARNING\b/gi,   `${C.yellow}WARNING${R}`)
      .replace(/\bERROR\b/gi,     `${C.red}ERROR${R}`)
      .replace(/\bFIX(?:ED)?\b/gi,`${C.green}$&${R}`)

    // Inline `code` and **bold** (only on original or already-replaced)
    return replaced
      .replace(/\*\*(.+?)\*\*/g, `${BOLD}$1${R}`)
      .replace(/`([^`]+)`/g,     `${C.cyan}$1${R}`)
  }

  // ── Colorize one line given code-block context ────────────────────────────
  function colorizeLine(line: string, inCode: boolean): string {
    if (!inCode) return colorizeProse(line)

    const t = line.trimStart()
    const indent = line.slice(0, line.length - t.length)

    // Diff +/- inside code blocks
    if (t.startsWith('+++ ') || t.startsWith('--- ')) return C.dim + line + R
    if (t.startsWith('+')) return C.green + '+' + R + highlightCode(indent + t.slice(1))
    if (t.startsWith('-')) return C.red   + '-' + R + highlightCode(indent + t.slice(1))
    if (t.startsWith('@@')) return C.cyan + DIM2 + line + R

    return highlightCode(line)
  }

  // ── Spinner ─────────────────────────────────────────────────────────────────
  const SPIN_FRAMES = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']
  let spinFrame = 0
  const spinInterval = setInterval(() => {
    spinFrame = (spinFrame + 1) % SPIN_FRAMES.length
    render()
  }, 80)

  // ── State ───────────────────────────────────────────────────────────────────
  const agents:   AgentRow[] = []
  const findings: Finding[]  = []
  const partials  = new Map<string, string>()   // agentName → streaming text so far

  let footerText   = `  ${C.dim}Running agents...${R}`
  let isComplete   = false
  let scrollOffset = 0
  let exitResolve: (() => void) | null = null

  // ── Key input ────────────────────────────────────────────────────────────────
  function onKey(chunk: Buffer) {
    const k = chunk.toString()
    if      (k === '\x1b[A' || k === 'k' || k === 'K') { scrollOffset++;                       render() }
    else if (k === '\x1b[B' || k === 'j' || k === 'J') { scrollOffset = Math.max(0, scrollOffset - 1);  render() }
    else if (k === '\x1b[5~' || k === 'u')             { scrollOffset += 10;                   render() }
    else if (k === '\x1b[6~' || k === 'd')             { scrollOffset = Math.max(0, scrollOffset - 10); render() }
    else if (k === 'g')                                 { scrollOffset = 999999;                render() }
    else if (k === 'G')                                 { scrollOffset = 0;                     render() }
    else if (isComplete) {
      exitResolve?.()
    }
  }

  if (process.stdin.isTTY) {
    process.stdin.setRawMode(true)
    process.stdin.resume()
    process.stdin.on('data', onKey)
  }

  process.stdout.on('resize', render)

  // ── Screen builder ───────────────────────────────────────────────────────────
  function buildScreen(): string {
    const cols    = Math.max(80, process.stdout.columns ?? 80)
    const rows    = Math.max(24, process.stdout.rows    ?? 24)
    const LEFT_W  = 28
    const DIV     = `${C.dim}│${R}`
    const RIGHT_W = Math.max(20, cols - LEFT_W - 4)
    const rule    = `  ${C.dim}${'─'.repeat(cols - 4)}${R}`

    const out: string[] = []

    // Header
    out.push(`  ${C.cyan}${BOLD}NEXARQ${R}  ${C.dim}·${R}  reviewing ${diffLineCount} diff lines`)
    out.push(rule)
    out.push(`${padR(`  ${C.dim}Agents${R}`, LEFT_W + 2)}${DIV}  ${C.dim}Findings${R}`)
    out.push(rule)

    // Left column — agents (spinner for running)
    const spin = SPIN_FRAMES[spinFrame] ?? '●'
    const leftLines: string[] = agents.length > 0
      ? agents.map((a) => {
          const icon = a.status === 'running' ? spin : ICON[a.status]
          return `  ${AGENT_COLOR[a.status]}${icon}${R}  ${AGENT_COLOR[a.status]}${a.name}${R}`
        })
      : [`  ${C.dim}Initialising...${R}`]

    // Right column — completed findings + live streaming partial outputs
    const rightLines: string[] = []
    for (const f of findings) {
      const label = f.severity.toUpperCase().padEnd(8)
      rightLines.push(`  ${sevColor(f.severity)}[${label}]${R}  ${BOLD}${f.agentName}${R}`)
      let inCode = false
      for (const raw of f.lines) {
        if (!raw.trim()) { rightLines.push(''); continue }
        const trimmed = raw.trimStart()
        if (trimmed.startsWith('```')) {
          inCode = !inCode
          rightLines.push(C.dim + raw.trimEnd() + R)
          continue
        }
        for (const piece of wrapPlain(raw, RIGHT_W - 4, '    ')) {
          rightLines.push(colorizeLine(piece, inCode))
        }
      }
      rightLines.push('')
    }

    // Streaming partial outputs for agents currently running
    for (const [agentName, text] of partials) {
      const agent = agents.find((a) => a.name === agentName)
      if (!agent || agent.status !== 'running') continue
      rightLines.push(`  ${C.cyan}${spin}${R}  ${C.cyan}${agentName}${R}  ${C.dim}generating...${R}`)
      // Show last 6 non-empty lines of the partial text
      const tail = text.split('\n').filter((l) => l.trim()).slice(-6)
      let inCode = false
      for (let i = 0; i < tail.length; i++) {
        const raw = tail[i] ?? ''
        if (raw.trimStart().startsWith('```')) { inCode = !inCode; rightLines.push(C.dim + '    ' + raw.trimEnd() + R); continue }
        const pieces = wrapPlain(raw, RIGHT_W - 4, '    ')
        for (let p = 0; p < pieces.length; p++) {
          const isLastPiece = i === tail.length - 1 && p === pieces.length - 1
          const piece = pieces[p] ?? ''
          rightLines.push(colorizeLine(piece, inCode) + (isLastPiece ? `${C.cyan}▌${R}` : ''))
        }
      }
      rightLines.push('')
    }

    // Body viewport
    const CHROME   = 7
    const bodyRows = Math.max(1, rows - CHROME)
    const maxScroll = Math.max(0, rightLines.length - bodyRows)
    scrollOffset    = Math.min(scrollOffset, maxScroll)
    const rightStart = maxScroll - scrollOffset
    const hasAbove   = rightStart > 0
    const hasBelow   = rightStart + bodyRows < rightLines.length

    for (let i = 0; i < bodyRows; i++) {
      const left = leftLines[i] ?? ''
      let right  = rightLines[rightStart + i] ?? ''
      if (i === 0 && hasAbove)           right = `  ${C.dim}↑  scroll up  (↑↓ / j k / u d / g G)${R}`
      if (i === bodyRows - 1 && hasBelow) right = `  ${C.dim}↓  more findings below${R}`
      out.push(`${padR(left, LEFT_W + 2)}${DIV}${right}`)
    }

    out.push(rule)

    const scrollHint = rightLines.length > bodyRows
      ? `  ${C.dim}│  ↑↓ scroll · g top · G bottom${R}`
      : ''
    out.push(footerText + scrollHint)

    return HOME_ERASE + out.join('\n')
  }

  function render() { process.stdout.write(buildScreen()) }

  process.stdout.write(ENTER_ALT)
  render()

  return {
    initAgents(names: string[]) {
      for (const name of names) agents.push({ name, status: 'pending' })
      render()
    },

    setAgentStatus(name: string, status: AgentStatus) {
      const row = agents.find((a) => a.name === name)
      if (row) row.status = status
      if (status !== 'running') partials.delete(name)
      render()
    },

    appendChunk(agentName: string, text: string) {
      partials.set(agentName, (partials.get(agentName) ?? '') + text)
      render()
    },

    addFinding(agentName: string, severity: string, lines: string[]) {
      partials.delete(agentName)   // clear partial — finding is now complete
      findings.push({ agentName, severity, lines })
      scrollOffset = 0
      render()
    },

    updateFooter(agentsRun: number, total: number, summary: Partial<RunSummary>, tokens: number) {
      const parts: string[] = [`  ${agentsRun}/${total} agents`]
      if ((summary.critical ?? 0) > 0) parts.push(`${C.critical}${BOLD}${summary.critical} critical${R}`)
      if ((summary.high     ?? 0) > 0) parts.push(`${C.high}${summary.high} high${R}`)
      if ((summary.medium   ?? 0) > 0) parts.push(`${C.medium}${summary.medium} medium${R}`)
      if ((summary.low      ?? 0) > 0) parts.push(`${C.low}${summary.low} low${R}`)
      if ((summary.info     ?? 0) > 0) parts.push(`${C.info}${summary.info} info${R}`)
      if (tokens > 0)                  parts.push(`${C.dim}${tokens.toLocaleString()} tokens${R}`)
      footerText = parts.join(`  ${C.dim}·${R}  `)
      render()
    },

    showComplete(durationMs: number) {
      isComplete = true
      clearInterval(spinInterval)
      partials.clear()
      const elapsed = (durationMs / 1000).toFixed(1)
      footerText = `  ${C.green}${BOLD}✓ Review complete${R}  ${C.dim}${elapsed}s  ·  any key to continue${R}`
      render()
      // Brief pause so the completion state is visible before the fix prompt
      setTimeout(() => exitResolve?.(), process.stdin.isTTY ? 800 : 100)
    },

    waitForExit(): Promise<void> {
      return new Promise((resolve) => { exitResolve = resolve })
    },

    destroy() {
      clearInterval(spinInterval)
      process.stdout.off('resize', render)
      process.stdout.write(EXIT_ALT)
      if (process.stdin.isTTY) {
        try { process.stdin.setRawMode(false); process.stdin.pause(); process.stdin.off('data', onKey) }
        catch { /* ignore */ }
      }
    },
  }
}
