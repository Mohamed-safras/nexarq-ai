import { tool } from '@langchain/core/tools'
import { HumanMessage, SystemMessage, AIMessage } from '@langchain/core/messages'
import { createReactAgent } from '@langchain/langgraph/prebuilt'
import { z } from 'zod'
import { execSync } from 'child_process'
import type { RunConfig, DiffResult } from '@nexarq/common/interfaces'
import type { RunEvent, ProviderName } from '@nexarq/common/types'
import { getReadTools } from './tools/read-tools.ts'
import { getTerminalTools } from './tools/terminal-tools.ts'
import { getShellTools } from './tools/shell-tools.ts'
import { getDocsTools } from './tools/docs-tools.ts'
import { getBrowserTools } from './tools/browser-tools.ts'
import { getProvider } from './providers/provider-factory.ts'
import { getAgent, getAllAgents } from './registry.ts'
import { runReactAgent } from './graph/nodes/workflow/node-utils.ts'
import {
  loadSession,
  saveSession,
  appendMessages,
  storeReview,
  pruneHistory,
  formatLastReviewContext,
  type SessionMessage,
  type StoredReview,
} from './session-store.ts'
import { runOrchestrator } from './orchestrator.ts'
import { runWorkflowOrchestrator } from './workflow-orchestrator.ts'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ConversationTurnOptions {
  userMessage: string
  workingDirectory: string
  runConfig?: RunConfig
  onEvent?: (event: RunEvent) => void
}

export interface ConversationTurnResult {
  response: string
  reviewTriggered: boolean
  sessionUpdated: boolean
  /** 3 suggested follow-up questions generated from this turn's context */
  suggestedFollowups: string[]
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function getRawDiff(workingDirectory: string, gitRef?: string): string {
  try {
    return execSync(`git diff ${gitRef ?? 'HEAD'}`, {
      cwd: workingDirectory, encoding: 'utf-8', timeout: 10_000,
    }).trim()
  } catch {
    return ''
  }
}

function makeDiffResult(rawDiff: string): DiffResult {
  return {
    rawDiff,
    files: [],
    totalAdded: 0,
    totalRemoved: 0,
    changeType: 'general',
    repoType: 'unknown',
    primaryLanguage: 'unknown',
  }
}

// ── System prompt ─────────────────────────────────────────────────────────────

const ORCHESTRATOR_SYSTEM = `You are Nexarq — an AI coding assistant and code review expert. You help developers write code, understand their codebase, review changes, and ship quality software.

Choose the right tool for each request:

CODING (general assistant)
- implement_task   → implement a feature, fix a bug, refactor code (full parallel workflow)
- run_shell        → install packages, run migrations, start dev server, deploy
- write_file       → (via coding workflow — prefer implement_task for multi-file changes)

REVIEW (code quality gate)
- trigger_review   → full 31-agent parallel review of current diff, severity-tagged findings
- spawn_review_agent → single specialist agent (faster, targeted domain)
- get_last_review  → recall findings from last review

RESEARCH
- read_docs        → fetch official library docs automatically (express, react, drizzle, etc.)
- web_search       → search for CVEs, Stack Overflow answers, changelogs
- read_file, search_code, list_directory, find_references → explore the codebase

VALIDATION
- run_validation   → run tsc / bun test / eslint (safe allowlist)
- run_shell        → broader commands when unsafeShell is enabled

BROWSER
- open_page        → navigate to a URL and read page content
- click_element, fill_form → interact with web pages
- take_screenshot  → capture visual state of current page
- get_page_text    → read text from current browser page

FOLLOW-UP
- suggest_followups → call after completing any substantial task to offer 3 next steps

Rules:
- Use implement_task for non-trivial coding requests; use run_shell for quick commands
- Use read_docs before guessing an API signature — it fetches the real docs
- Use trigger_review when the user asks to scan/review/check the diff
- Always cite file:line when referencing a code issue
- Keep responses concise — bullets over paragraphs
- After trigger_review, implement_task, or spawn_review_agent, call suggest_followups

If you see a [CONVERSATION SUMMARY] block in history, it is condensed prior context — do not re-read or re-summarise it.`

// ── Meta-tools ────────────────────────────────────────────────────────────────

function buildMetaTools(
  workingDirectory: string,
  runConfig: RunConfig,
  onEvent: ((event: RunEvent) => void) | undefined,
  getLastReview: () => StoredReview | null,
  setLastReview: (r: StoredReview) => void,
) {
  // ── trigger_review: full parallel fan-out ────────────────────────────────
  const triggerReviewTool = tool(
    async ({ gitRef }: { gitRef?: string }): Promise<string> => {
      try {
        const rawDiff = getRawDiff(workingDirectory, gitRef)
        if (!rawDiff) return 'No diff found. Make sure there are uncommitted changes or specify a git ref.'

        const result = await runOrchestrator({
          diffResult: makeDiffResult(rawDiff),
          triggerSource: 'on-demand',
          workingDirectory,
          runConfig,
          ...(onEvent ? { onEvent } : {}),
        })

        setLastReview({
          summary: result.summary,
          findings: result.results.flatMap((r) => r.findings),
          fullOutput: result.finalOutput,
          workingDirectory,
          timestamp: Date.now(),
        })

        const { summary } = result
        const topFindings = result.results
          .filter((r) => r.severity === 'critical' || r.severity === 'high')
          .flatMap((r) => r.findings)
          .slice(0, 5)
          .map((f) => `  - ${f.file ?? ''}${f.line ? `:${f.line}` : ''} — ${f.message}`)

        return [
          `Review complete (${result.durationMs}ms): ${summary.critical} critical · ${summary.high} high · ${summary.medium} medium · ${summary.low} low`,
          topFindings.length > 0 ? `\nTop findings:\n${topFindings.join('\n')}` : '\nNo critical/high findings.',
        ].join('')
      } catch (err) {
        return `Review failed: ${err instanceof Error ? err.message : String(err)}`
      }
    },
    {
      name: 'trigger_review',
      description:
        'Run the full 31-agent parallel Nexarq review on the current git diff. ' +
        'Returns structured findings grouped by severity. Best for a complete scan.',
      schema: z.object({
        gitRef: z.string().optional().describe('Git ref to diff against (default: working tree vs HEAD)'),
      }),
    }
  )

  // ── spawn_review_agent: targeted single-agent run (hierarchical delegation) ─
  const spawnReviewAgentTool = tool(
    async ({ agentName, focusContext }: { agentName: string; focusContext?: string }): Promise<string> => {
      const agentDef = getAgent(agentName)
      if (!agentDef) {
        const available = getAllAgents().map((agent: { name: string }) => agent.name).join(', ')
        return `Unknown agent "${agentName}". Available: ${available}`
      }

      const rawDiff = getRawDiff(workingDirectory)
      if (!rawDiff) return 'No diff to analyze.'

      const prompt = agentDef.buildPrompt(rawDiff, 'unknown', focusContext)
      const tools = getReadTools(workingDirectory)

      const output = await runReactAgent(runConfig, agentDef.systemPrompt, prompt, tools, {
        temperature: 0.2,
        maxTokens: 2048,
      })

      // Merge into last review findings if we have one
      const existing = getLastReview()
      if (existing && agentDef.parseFindingsFromOutput) {
        const newFindings = agentDef.parseFindingsFromOutput(output)
        setLastReview({
          ...existing,
          findings: [...existing.findings, ...newFindings],
          timestamp: Date.now(),
        })
      }

      return `[${agentDef.displayName}]\n${output}`
    },
    {
      name: 'spawn_review_agent',
      description:
        'Run a single Nexarq specialist agent on the current diff. ' +
        'Faster than trigger_review — use when you need one domain analysed (e.g. "security", "bugs", "deep_analysis", "performance").',
      schema: z.object({
        agentName: z.string().describe('Agent name, e.g. "security", "bugs", "deep_analysis", "type_safety"'),
        focusContext: z.string().optional().describe('Extra context or focus hint for the agent'),
      }),
    }
  )

  // ── get_last_review: recall persisted findings ───────────────────────────
  const getLastReviewTool = tool(
    async (): Promise<string> => {
      const review = getLastReview()
      if (!review) return 'No review yet in this session. Use trigger_review to run one.'
      return formatLastReviewContext(review)
    },
    {
      name: 'get_last_review',
      description: 'Retrieve findings from the most recent review run in this session.',
      schema: z.object({}),
    }
  )

  // ── suggest_followups: Codebuff-style next-step suggestions ─────────────
  const suggestFollowupsTool = tool(
    async ({ suggestions }: { suggestions: string[] }): Promise<string> => {
      // The agent populates the list; we just store it and echo it back
      return `Suggested next steps:\n${suggestions.map((s, i) => `${i + 1}. ${s}`).join('\n')}`
    },
    {
      name: 'suggest_followups',
      description:
        'After completing a review or analysis, call this with 3 concrete suggested next steps ' +
        'the developer might want to take (e.g. "Fix the SQL injection in auth.ts", "Run tsc to check types", "Review the dependency update").',
      schema: z.object({
        suggestions: z.array(z.string()).min(1).max(5).describe('List of 3–5 suggested next steps'),
      }),
    }
  )

  // ── implement_task: general coding assistant (reuses full coding workflow) ──
  const implementTaskTool = tool(
    async ({ task }: { task: string }): Promise<string> => {
      try {
        const result = await runWorkflowOrchestrator({
          task,
          workingDirectory,
          runConfig,
          ...(onEvent ? { onEvent } : {}),
        })

        const files = result.modifiedFiles.length > 0
          ? `\nModified files:\n${result.modifiedFiles.map((f) => `  - ${f}`).join('\n')}`
          : ''
        const errors = result.coderOutputs.filter((o) => o.error).map((o) => `  - subtask ${o.subtaskId}: ${o.error}`)
        const errorBlock = errors.length > 0 ? `\nErrors:\n${errors.join('\n')}` : ''

        return [
          `Task complete (${result.durationMs}ms) — ${result.subtasksCompleted} subtask(s)`,
          files,
          errorBlock,
          result.reviewerOutput ? `\nReviewer notes:\n${result.reviewerOutput.slice(0, 800)}` : '',
        ].filter(Boolean).join('')
      } catch (err) {
        return `Task failed: ${err instanceof Error ? err.message : String(err)}`
      }
    },
    {
      name: 'implement_task',
      description:
        'Implement a coding task using the full multi-agent coding workflow: ' +
        'planner → architect → parallel coders → tester → reviewer. ' +
        'Use for non-trivial coding requests: "add a login endpoint", "refactor the auth module", "write tests for UserService".',
      schema: z.object({
        task: z.string().describe('Clear description of what to implement, refactor, or fix'),
      }),
    }
  )

  return [triggerReviewTool, spawnReviewAgentTool, getLastReviewTool, suggestFollowupsTool, implementTaskTool]
}

// ── Conversation turn ─────────────────────────────────────────────────────────

/**
 * Runs a single conversational turn with the Nexarq orchestrator.
 *
 * Features (inspired by Codebuff's Buffy orchestrator):
 * - Persistent conversation history via session-store (.nexarq/session.json)
 * - Context pruning: old messages auto-condensed when history > 30 entries
 * - Full tool suite: review, spawn-agent, read, terminal, web-search
 * - Suggest followups: agent proposes 3 next steps after substantive turns
 * - Review memory: last review findings injected into system prompt each turn
 */
export async function runConversationTurn(
  options: ConversationTurnOptions
): Promise<ConversationTurnResult> {
  const { userMessage, workingDirectory, runConfig = {}, onEvent } = options

  const session = loadSession(workingDirectory)
  let lastReview: StoredReview | null = session.lastReview
  let reviewTriggered = false
  const capturedFollowups: string[] = []

  const setLastReview = (r: StoredReview) => { lastReview = r; reviewTriggered = true }

  // ── Tool set ─────────────────────────────────────────────────────────────
  const metaTools = buildMetaTools(workingDirectory, runConfig, onEvent, () => lastReview, setLastReview)
  const allTools = [
    ...getReadTools(workingDirectory),
    ...getTerminalTools(workingDirectory),
    ...getShellTools(workingDirectory, runConfig.unsafeShell ?? false),
    ...getDocsTools(),
    ...getBrowserTools(),
    ...metaTools,
  ]

  // ── Chat model ───────────────────────────────────────────────────────────
  const providerName = (runConfig.provider ?? 'ollama') as ProviderName
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chatModel = getProvider(providerName).buildModel({
    ...(runConfig.model ? { model: runConfig.model } : {}),
    temperature: 0.3,
    maxTokens: 4096,
  }) as any

  // ── System prompt (injects last review context) ───────────────────────────
  const lastReviewBlock = lastReview
    ? `\n\n--- LAST REVIEW ---\n${formatLastReviewContext(lastReview)}\n--- END LAST REVIEW ---`
    : ''
  const systemPrompt = ORCHESTRATOR_SYSTEM + lastReviewBlock

  // ── Context-pruned history ────────────────────────────────────────────────
  // Prune deterministically (no LLM needed) so the context window never overflows
  const prunedHistory = pruneHistory(session.conversationHistory, 30)
  const historyMessages = prunedHistory.map((m): HumanMessage | AIMessage =>
    m.role === 'user' ? new HumanMessage(m.content) : new AIMessage(m.content)
  )

  // ── Run agent ────────────────────────────────────────────────────────────
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const agent = createReactAgent({ llm: chatModel, tools: allTools as any[] })

  const result = await agent.invoke({
    messages: [
      new SystemMessage(systemPrompt),
      ...historyMessages,
      new HumanMessage(userMessage),
    ],
  }) as { messages: Array<{ content: unknown }> }

  // Extract text from the last message (may be content array if extended thinking used)
  const lastMsg = result.messages.at(-1)
  let response = ''
  if (lastMsg) {
    if (Array.isArray(lastMsg.content)) {
      response = lastMsg.content
        .filter((b): b is { type: string; text: string } =>
          typeof b === 'object' && b !== null && (b as { type?: string }).type === 'text'
        )
        .map((b) => b.text)
        .join('')
    } else {
      response = String(lastMsg.content)
    }
  }

  // Extract any suggest_followups the agent called during this turn
  for (const msg of result.messages) {
    if (Array.isArray(msg.content)) {
      for (const block of msg.content) {
        if (
          typeof block === 'object' && block !== null &&
          (block as { type?: string }).type === 'tool_use' &&
          (block as { name?: string }).name === 'suggest_followups'
        ) {
          const input = (block as { input?: { suggestions?: string[] } }).input
          if (input?.suggestions) capturedFollowups.push(...input.suggestions)
        }
      }
    }
  }

  // ── Persist ───────────────────────────────────────────────────────────────
  const newMessages: SessionMessage[] = [
    { role: 'user', content: userMessage, timestamp: Date.now() },
    { role: 'assistant', content: response, timestamp: Date.now() },
  ]

  let updatedSession = appendMessages(session, newMessages)
  if (reviewTriggered && lastReview) updatedSession = storeReview(updatedSession, lastReview)
  saveSession(workingDirectory, updatedSession)

  return {
    response,
    reviewTriggered,
    sessionUpdated: true,
    suggestedFollowups: capturedFollowups,
  }
}
