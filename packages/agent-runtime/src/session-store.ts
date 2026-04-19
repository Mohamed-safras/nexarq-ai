import type { AgentFinding, RunSummary } from '@nexarq/common/interfaces'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'fs'
import { join, resolve } from 'path'

// ── Types ────────────────────────────────────────────────────────────────────

export interface SessionMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export interface StoredReview {
  summary: RunSummary
  /** Flat list of all findings from all agents — for the orchestrator to reference */
  findings: AgentFinding[]
  /** Full text output from the review run */
  fullOutput: string
  workingDirectory: string
  timestamp: number
}

export interface ReviewSession {
  workingDirectory: string
  conversationHistory: SessionMessage[]
  lastReview: StoredReview | null
  lastUpdated: number
}

// ── Storage path ─────────────────────────────────────────────────────────────

function sessionPath(workingDirectory: string): string {
  const dir = join(resolve(workingDirectory), '.nexarq')
  mkdirSync(dir, { recursive: true })
  return join(dir, 'session.json')
}

// ── Public API ───────────────────────────────────────────────────────────────

export function loadSession(workingDirectory: string): ReviewSession {
  const path = sessionPath(workingDirectory)
  if (!existsSync(path)) {
    return {
      workingDirectory: resolve(workingDirectory),
      conversationHistory: [],
      lastReview: null,
      lastUpdated: Date.now(),
    }
  }
  try {
    const raw = readFileSync(path, 'utf-8')
    return JSON.parse(raw) as ReviewSession
  } catch {
    return {
      workingDirectory: resolve(workingDirectory),
      conversationHistory: [],
      lastReview: null,
      lastUpdated: Date.now(),
    }
  }
}

export function saveSession(workingDirectory: string, session: ReviewSession): void {
  const path = sessionPath(workingDirectory)
  writeFileSync(path, JSON.stringify({ ...session, lastUpdated: Date.now() }, null, 2), 'utf-8')
}

export function clearSession(workingDirectory: string): void {
  const path = sessionPath(workingDirectory)
  if (existsSync(path)) {
    writeFileSync(
      path,
      JSON.stringify({
        workingDirectory: resolve(workingDirectory),
        conversationHistory: [],
        lastReview: null,
        lastUpdated: Date.now(),
      } satisfies ReviewSession, null, 2),
      'utf-8'
    )
  }
}

/** Append a user/assistant exchange and trim history to last N turns. */
export function appendMessages(
  session: ReviewSession,
  messages: SessionMessage[],
  maxTurns = 40
): ReviewSession {
  const updated = [...session.conversationHistory, ...messages]
  // Keep only the last maxTurns messages (each turn = user + assistant = 2 messages)
  const trimmed = updated.length > maxTurns ? updated.slice(-maxTurns) : updated
  return { ...session, conversationHistory: trimmed, lastUpdated: Date.now() }
}

/** Store the result of a completed review run into the session. */
export function storeReview(
  session: ReviewSession,
  review: StoredReview
): ReviewSession {
  return { ...session, lastReview: review, lastUpdated: Date.now() }
}

/**
 * Context pruner — fires when conversation history exceeds `maxMessages`.
 * Older messages are condensed into a single summary message so the LLM
 * context window never overflows
 *
 * Pure and deterministic — no LLM call needed. Extracts the most signal-dense
 * lines from each message (FINDING:, SUGGESTION:, key user questions).
 */
export function pruneHistory(history: SessionMessage[], maxMessages = 30): SessionMessage[] {
  if (history.length <= maxMessages) return history

  // Keep the most recent half; condense everything older
  const keepCount = Math.floor(maxMessages / 2)
  const toCondense = history.slice(0, -keepCount)
  const toKeep = history.slice(-keepCount)

  const condensedLines: string[] = ['[CONVERSATION SUMMARY — earlier messages condensed]', '']

  for (const msg of toCondense) {
    const prefix = msg.role === 'user' ? '[USER]' : '[ASSISTANT]'
    const lines = msg.content.split('\n')

    // Extract the highest-signal lines: findings, user questions, short statements
    const keyLines = lines
      .filter((line) =>
        line.startsWith('FINDING:') ||
        line.startsWith('TRIAGE-FINDING:') ||
        line.startsWith('VALIDATION:') ||
        line.startsWith('RECOMMENDATION:') ||
        line.startsWith('RISK SCORE:') ||
        (msg.role === 'user' && line.trim().length > 0)
      )
      .slice(0, 5)
      .map((l) => `  ${l.trim()}`)

    if (keyLines.length > 0) {
      condensedLines.push(`${prefix}`)
      condensedLines.push(...keyLines)
      condensedLines.push('')
    } else if (msg.role === 'user') {
      // Always include user messages — they carry intent
      condensedLines.push(`${prefix} ${msg.content.slice(0, 200).replace(/\n/g, ' ')}`)
      condensedLines.push('')
    }
  }

  const summaryMessage: SessionMessage = {
    role: 'assistant',
    content: condensedLines.join('\n'),
    timestamp: toCondense[toCondense.length - 1]?.timestamp ?? Date.now(),
  }

  return [summaryMessage, ...toKeep]
}

/** Format the last review as a concise context block for the orchestrator. */
export function formatLastReviewContext(lastReview: StoredReview): string {
  const age = Math.round((Date.now() - lastReview.timestamp) / 60_000)
  const ageLabel = age < 1 ? 'just now' : age === 1 ? '1 minute ago' : `${age} minutes ago`

  const findingLines = lastReview.findings
    .slice(0, 20)
    .map((finding) => `  - ${finding.file ?? ''}${finding.line ? `:${finding.line}` : ''} — ${finding.message}`)
    .join('\n')

  return [
    `Last review (${ageLabel}):`,
    `  ${lastReview.summary.critical} critical · ${lastReview.summary.high} high · ` +
    `${lastReview.summary.medium} medium · ${lastReview.summary.low} low`,
    findingLines.length > 0 ? `Top findings:\n${findingLines}` : '  No structured findings recorded.',
  ].join('\n')
}
