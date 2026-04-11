import type { BaseMessage } from '@langchain/core/messages'
import type { DiffResult, RunConfig, AgentResult } from '@nexarq/common/interfaces'
import type { TriggerSource } from '../selector.ts'

/**
 * The shape of the shared state flowing through the LangGraph graph.
 * Both the code-review path and the coding-agent path share this state —
 * nodes only touch the fields relevant to their task.
 */
export interface NexarqGraphState {
  // ── Inputs ──────────────────────────────────────────────────────────────────
  /** The task description — a review request or a coding instruction */
  task: string
  /** Source that triggered this run */
  triggerSource: TriggerSource
  /** Parsed diff for review tasks; undefined for coding-agent tasks */
  diffResult?: DiffResult | undefined
  /** Runtime configuration */
  runConfig: RunConfig
  /** LangChain message history for the current turn */
  messages: BaseMessage[]

  // ── Runtime ─────────────────────────────────────────────────────────────────
  /** Which agent names have been dispatched in this run */
  dispatchedAgents: string[]
  /** Accumulated results from all review agents */
  agentResults: AgentResult[]
  /** Whether any CRITICAL or HIGH severity finding was found */
  hasHighSeverityFinding: boolean
  /** Tool call count guard — prevents runaway loops */
  toolCallCount: number
  /** Working directory for coding-agent file operations */
  workingDirectory?: string
  /** Files changed by the coding agent during this run */
  modifiedFiles: string[]
  /** Content from NEXARQ.md / .nexarq/knowledge.md injected into all prompts */
  knowledgeContext?: string

  // ── Output ──────────────────────────────────────────────────────────────────
  /** Final assembled output text */
  finalOutput: string
  /** Whether the graph has finished */
  isDone: boolean
  /** Error message if the run failed */
  errorMessage?: string
}

// Only required / non-optional fields are listed here.
// Optional fields (diffResult, workingDirectory, knowledgeContext, errorMessage)
// are omitted so exactOptionalPropertyTypes is satisfied.
export const GRAPH_STATE_DEFAULTS = {
  messages:               [] as BaseMessage[],
  dispatchedAgents:       [] as string[],
  agentResults:           [] as AgentResult[],
  hasHighSeverityFinding: false,
  toolCallCount:          0,
  modifiedFiles:          [] as string[],
  finalOutput:            '',
  isDone:                 false,
} as const satisfies Partial<NexarqGraphState>
