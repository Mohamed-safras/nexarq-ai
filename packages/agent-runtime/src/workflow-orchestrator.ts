import type { RunConfig } from '@nexarq/common/interfaces'
import type { RunEvent } from '@nexarq/common/types'
import { loadKnowledgeFile, formatKnowledgeBlock } from './knowledge.ts'
import { runPlannerAgent } from './graph/nodes/workflow/planner-node.ts'
import { buildCodingGraph } from './graph/graph.ts'
import { GRAPH_STATE_DEFAULTS, type NexarqGraphState } from './graph/state.ts'

export interface WorkflowRunOptions {
  /** The coding task to execute */
  task: string
  /** Absolute path to the project root */
  workingDirectory?: string
  /** Runtime configuration */
  runConfig?: RunConfig
  /** Streaming event callback */
  onEvent?: (event: RunEvent) => void
}

export interface WorkflowRunResult {
  planSummary: string
  subtasksCompleted: number
  architectOutput: string
  coderOutputs: Array<{ subtaskId: string; output: string; modifiedFiles: string[]; error?: string }>
  testerOutput: string
  reviewerOutput: string
  modifiedFiles: string[]
  durationMs: number
}

/**
 * Entry point for the parallel multi-agent coding workflow.
 *
 * Stage flow:
 *   1. Planner  — explores codebase, produces parallelizable subtask plan
 *   2. Architect — designs solution based on plan (read-only exploration)
 *   3. Coders   — implement each subtask in parallel (read + write tools)
 *   4. Tester   — writes and runs tests for all changes
 *   5. Reviewer — synthesizes all outputs into a final developer report
 */
export async function runWorkflowOrchestrator(
  options: WorkflowRunOptions
): Promise<WorkflowRunResult> {
  const startTime = Date.now()

  const {
    task,
    workingDirectory = process.cwd(),
    runConfig = {},
    onEvent,
  } = options

  // Load project knowledge (NEXARQ.md or .nexarq/knowledge.md)
  const rawKnowledge = loadKnowledgeFile(workingDirectory)
  const knowledgeContext = rawKnowledge ? formatKnowledgeBlock(rawKnowledge) : undefined

  // ── Stage 1: Planning (before graph) ──────────────────────────────────────
  const plan = await runPlannerAgent(
    task,
    runConfig,
    workingDirectory,
    knowledgeContext,
    onEvent
  )

  // ── Stages 2–5: Build graph with correct coder count, then run ────────────
  const graph = buildCodingGraph(plan.subtasks)

  const agentNames = [
    'planner',
    'architect',
    ...plan.subtasks.map((s) => `coder-${s.id}`),
    'tester',
    'reviewer',
  ]
  onEvent?.({ type: 'run:plan', agentNames })

  const initialState: NexarqGraphState = {
    ...GRAPH_STATE_DEFAULTS,
    task,
    triggerSource: 'on-demand',
    workingDirectory,
    runConfig,
    subtasks: plan.subtasks,
    planSummary: plan.planSummary,
    ...(knowledgeContext ? { knowledgeContext } : {}),
    ...(onEvent ? { onEvent } : {}),
  }

  const finalState: NexarqGraphState = await graph.invoke(initialState)

  onEvent?.({
    type: 'run:complete',
    results: [],
    durationMs: Date.now() - startTime,
  })

  return {
    planSummary:        finalState.planSummary,
    subtasksCompleted:  finalState.coderResults.filter((r: { error?: string }) => !r.error).length,
    architectOutput:    finalState.architectOutput,
    coderOutputs:       finalState.coderResults,
    testerOutput:       finalState.testerOutput,
    reviewerOutput:     finalState.reviewerOutput,
    modifiedFiles:      finalState.modifiedFiles,
    durationMs:         Date.now() - startTime,
  }
}
