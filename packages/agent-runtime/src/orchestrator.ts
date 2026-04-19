import type { AgentMode, RunEvent } from '@nexarq/common/types'
import type { AgentResult, DiffResult, RunConfig, RunResponse, RunSummary } from '@nexarq/common/interfaces'
import { DEFAULT_MODE, DEFAULT_MAX_AGENTS } from '@nexarq/common/constants'
import { compareSeverity } from '@nexarq/common/utils'
import { selectAgents, type TriggerSource } from './selector.ts'
import { buildNexarqGraph } from './graph/graph.ts'
import { GRAPH_STATE_DEFAULTS, type NexarqGraphState } from './graph/state.ts'

import { loadKnowledgeFile, formatKnowledgeBlock } from './knowledge.ts'

export interface OrchestratorRunOptions {
  /** Free-text task description (used for coding-agent mode) */
  task?: string
  /** Parsed diff (used for review mode) */
  diffResult?: DiffResult
  /** Where the run was triggered from */
  triggerSource: TriggerSource
  /** Runtime configuration overrides */
  runConfig?: RunConfig
  /** Absolute path to the project root */
  workingDirectory?: string
  /** Callback fired as each agent completes — enables streaming output */
  onEvent?: (event: RunEvent) => void
}

export interface OrchestratorRunResult {
  results: AgentResult[]
  summary: RunSummary
  finalOutput: string
  durationMs: number
  triggerSource: TriggerSource
}

/**
 * The single entry point for every Nexarq agent run, regardless of surface.
 *
 * Called by:
 *   - CLI commands (nexarq run, nexarq code, git hooks)
 *   - Web API route (POST /api/v1/run)
 *   - SDK (NexarqClient.run())
 *
 * Internally builds the LangGraph graph and invokes it with the correct
 * initial state. LangSmith tracing is applied transparently when configured.
 */
export async function runOrchestrator(
  options: OrchestratorRunOptions
): Promise<OrchestratorRunResult> {
  const startTime = Date.now()

  const {
    task = '',
    diffResult,
    triggerSource,
    runConfig = {},
    workingDirectory = process.cwd(),
    onEvent,
  } = options

  const resolvedMode: AgentMode = runConfig.mode ?? DEFAULT_MODE

  const selectionPlan = selectAgents({
    ...(diffResult ? { diffResult } : {}),
    mode: resolvedMode,
    triggerSource,
    ...(runConfig.agents ? { requestedAgentNames: runConfig.agents } : {}),
    maxAgents: runConfig.maxAgents ?? DEFAULT_MAX_AGENTS,
  })

  const agentNames = selectionPlan.allSelectedAgents.map((agentDef) => agentDef.name)

  // Announce the plan so the TUI can show all agents as pending before the graph starts
  onEvent?.({ type: 'run:plan', agentNames })
  for (const agentName of agentNames) {
    onEvent?.({ type: 'agent:start', agentName })
  }

  // Load project knowledge file — injected as context into every agent prompt
  const rawKnowledge = loadKnowledgeFile(workingDirectory)
  const knowledgeContext = rawKnowledge ? formatKnowledgeBlock(rawKnowledge) : undefined

  const initialState: NexarqGraphState = {
    ...GRAPH_STATE_DEFAULTS,
    task,
    triggerSource,
    runConfig,
    workingDirectory,
    ...(diffResult ? { diffResult } : {}),
    ...(knowledgeContext ? { knowledgeContext } : {}),
    ...(onEvent ? { onEvent } : {}),
  }

  const graph = buildNexarqGraph(selectionPlan)

  const finalState = await graph.invoke(initialState)

  const durationMs = Date.now() - startTime
  const sortedResults = [...finalState.agentResults].sort((resultA, resultB) =>
    compareSeverity(resultA.severity, resultB.severity)
  )

  const summary = buildSummary(sortedResults)

  onEvent?.({ type: 'run:complete', results: sortedResults, durationMs })

  return {
    results: sortedResults,
    summary,
    finalOutput: finalState.finalOutput,
    durationMs,
    triggerSource,
  }
}

function buildSummary(results: AgentResult[]): RunSummary {
  return {
    totalFindings: results.reduce((total, result) => total + result.findings.length, 0),
    critical:      results.filter((result) => result.severity === 'critical').length,
    high:          results.filter((result) => result.severity === 'high').length,
    medium:        results.filter((result) => result.severity === 'medium').length,
    low:           results.filter((result) => result.severity === 'low').length,
    info:          results.filter((result) => result.severity === 'info').length,
    agentsRun:     results.map((result) => result.agentName),
    tokensUsed:    results.reduce((total, result) => total + result.tokenUsage.totalTokens, 0),
    estimatedCostUsd: results.reduce(
      (total, result) => total + (result.tokenUsage.estimatedCostUsd ?? 0), 0
    ),
  }
}

export function buildRunResponse(result: OrchestratorRunResult): RunResponse {
  return {
    runId: crypto.randomUUID(),
    results: result.results,
    durationMs: result.durationMs,
    summary: result.summary,
  }
}
