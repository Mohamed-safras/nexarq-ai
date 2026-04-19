import type { BaseMessage } from '@langchain/core/messages'
import type { DiffResult, RunConfig, AgentResult } from '@nexarq/common/interfaces'
import type { RunEvent } from '@nexarq/common/types'
import type { TriggerSource } from '../selector.ts'

// ── Coding workflow types ────────────────────────────────────────────────────

export interface WorkflowSubtask {
  id: string
  title: string
  description: string
  targetFiles?: string[]
}

export interface WorkflowCoderResult {
  subtaskId: string
  output: string
  modifiedFiles: string[]
  error?: string
}

// ── Unified graph state ──────────────────────────────────────────────────────

/**
 * Single shared state for all Nexarq graph flows.
 *
 * Review flow uses: diffResult, agentResults, hasHighSeverityFinding,
 *                   dispatchedAgents, toolCallCount, finalOutput
 * Coding flow uses: subtasks, planSummary, architectOutput,
 *                   coderResults, testerOutput, reviewerOutput
 *
 * Nodes only read/write the fields relevant to their path.
 */
export interface NexarqGraphState {
  // ── Common ──────────────────────────────────────────────────────────────────
  task: string
  triggerSource: TriggerSource
  runConfig: RunConfig
  workingDirectory?: string
  messages: BaseMessage[]
  modifiedFiles: string[]
  isDone: boolean
  errorMessage?: string
  knowledgeContext?: string
  onEvent?: (event: RunEvent) => void

  // ── Review flow ─────────────────────────────────────────────────────────────
  diffResult?: DiffResult
  dispatchedAgents: string[]
  agentResults: AgentResult[]
  hasHighSeverityFinding: boolean
  toolCallCount: number
  finalOutput: string

  // ── Triage (post-fanout dynamic orchestration) ──────────────────────────────
  /**
   * Output from the triage node — additional findings or validation results
   * discovered after the parallel fan-out. Merged into finalOutput by summary-node.
   */
  triageOutput: string

  // ── Coding flow ─────────────────────────────────────────────────────────────
  subtasks: WorkflowSubtask[]
  planSummary: string
  architectOutput: string
  coderResults: WorkflowCoderResult[]
  testerOutput: string
  reviewerOutput: string
}

export const GRAPH_STATE_DEFAULTS = {
  messages:               [] as BaseMessage[],
  dispatchedAgents:       [] as string[],
  agentResults:           [] as AgentResult[],
  hasHighSeverityFinding: false,
  toolCallCount:          0,
  modifiedFiles:          [] as string[],
  finalOutput:            '',
  isDone:                 false,
  triageOutput:           '',
  subtasks:               [] as WorkflowSubtask[],
  planSummary:            '',
  architectOutput:        '',
  coderResults:           [] as WorkflowCoderResult[],
  testerOutput:           '',
  reviewerOutput:         '',
} as const satisfies Partial<NexarqGraphState>

export function buildStateChannels(): Record<string, unknown> {
  return {
    // Common
    task:                   { default: () => '' },
    triggerSource:          { default: () => 'on-demand' },
    runConfig:              { default: () => ({}) },
    workingDirectory:       { default: () => undefined },
    messages:               { reducer: (a: BaseMessage[], b: BaseMessage[]) => [...a, ...b], default: () => [] },
    modifiedFiles:          { reducer: (a: string[], b: string[]) => [...new Set([...a, ...b])], default: () => [] },
    isDone:                 { default: () => false },
    errorMessage:           { default: () => undefined },
    knowledgeContext:       { default: () => undefined },
    onEvent:                { default: () => undefined },

    // Review flow
    diffResult:             { default: () => undefined },
    dispatchedAgents:       { reducer: (a: string[], b: string[]) => [...a, ...b], default: () => [] },
    agentResults:           { reducer: (a: unknown[], b: unknown[]) => [...a, ...b], default: () => [] },
    hasHighSeverityFinding: { reducer: (a: boolean, b: boolean) => a || b, default: () => false },
    toolCallCount:          { default: () => 0 },
    finalOutput:            { default: () => '' },

    // Triage
    triageOutput:           { default: () => '' },

    // Coding flow
    subtasks:               { default: () => [] },
    planSummary:            { default: () => '' },
    architectOutput:        { default: () => '' },
    coderResults:           { reducer: (a: WorkflowCoderResult[], b: WorkflowCoderResult[]) => [...a, ...b], default: () => [] },
    testerOutput:           { default: () => '' },
    reviewerOutput:         { default: () => '' },
  }
}
