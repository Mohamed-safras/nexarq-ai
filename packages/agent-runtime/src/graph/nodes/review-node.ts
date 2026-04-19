import { isHighPriority } from '@nexarq/common/utils'
import type { AgentResult } from '@nexarq/common/interfaces'
import type { NexarqGraphState } from '../state.ts'
import { getAgent } from '../../registry.ts'
import { MODE_MAX_DIFF_TOKENS, MODE_MAX_OUTPUT_TOKENS } from '@nexarq/common/constants'
import { runReactAgent, runThinkingAgent, fireComplete } from './workflow/node-utils.ts'
import { getReadTools } from '../../tools/index.ts'

function truncateDiff(rawDiff: string, maxTokens: number): string {
  const maxChars = maxTokens * 4
  if (rawDiff.length <= maxChars) return rawDiff
  return rawDiff.slice(0, maxChars) + '\n\n[diff truncated for speed — use --mode deep for full analysis]'
}

/**
 * Runs a single named review agent as a ReAct loop with read-only tools.
 * The agent receives the diff in its prompt and can explore the codebase
 * for context before producing its findings.
 *
 * Each agent gets its own node invocation — LangGraph fans them out in
 * parallel via the orchestrator's conditional edges.
 */
export async function runReviewAgentNode(
  state: NexarqGraphState,
  agentName: string
): Promise<Partial<NexarqGraphState>> {
  const agentDefinition = getAgent(agentName)
  if (!agentDefinition) {
    return { agentResults: [...state.agentResults, buildErrorResult(agentName, `Agent "${agentName}" not found in registry`)] }
  }

  const diffResult = state.diffResult
  if (!diffResult) {
    return { agentResults: [...state.agentResults, buildErrorResult(agentName, 'No diff result available')] }
  }

  const mode            = state.runConfig.mode ?? 'smart'
  const maxDiffTokens   = MODE_MAX_DIFF_TOKENS[mode]
  const maxOutputTokens = MODE_MAX_OUTPUT_TOKENS[mode]

  const truncatedDiff = truncateDiff(diffResult.rawDiff, maxDiffTokens)
  const userPrompt    = agentDefinition.buildPrompt(truncatedDiff, diffResult.primaryLanguage)

  const workingDirectory = state.workingDirectory ?? process.cwd()
  const tools            = getReadTools(workingDirectory)

  const startTime = Date.now()
  state.onEvent?.({ type: 'agent:start', agentName })

  try {
    const runAgent = agentDefinition.usesExtendedThinking ? runThinkingAgent : runReactAgent
    const output = await runAgent(
      state.runConfig,
      agentDefinition.systemPrompt,
      userPrompt,
      tools,
      { temperature: 0.2, maxTokens: maxOutputTokens }
    )

    const findings = agentDefinition.parseFindingsFromOutput?.(output) ?? []

    const agentResult: AgentResult = {
      agentName,
      severity:   agentDefinition.severity,
      output,
      findings,
      warnings:   [],
      tokenUsage: { promptTokens: 0, completionTokens: 0, totalTokens: 0 },
      latencyMs:  Date.now() - startTime,
      cached:     false,
    }

    fireComplete(state.onEvent, agentName, output, Date.now() - startTime)

    const updatedResults  = [...state.agentResults, agentResult]
    const hasHighSeverity = updatedResults.some((r) => isHighPriority(r.severity))

    return {
      agentResults:           updatedResults,
      dispatchedAgents:       [...state.dispatchedAgents, agentName],
      hasHighSeverityFinding: hasHighSeverity,
    }
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : String(err)
    state.onEvent?.({ type: 'agent:error', agentName, error: errorMessage })
    return {
      agentResults:     [...state.agentResults, buildErrorResult(agentName, errorMessage)],
      dispatchedAgents: [...state.dispatchedAgents, agentName],
    }
  }
}

function buildErrorResult(agentName: string, errorMessage: string): AgentResult {
  return {
    agentName,
    severity:   'info',
    output:     '',
    findings:   [],
    warnings:   [],
    tokenUsage: { promptTokens: 0, completionTokens: 0, totalTokens: 0 },
    latencyMs:  0,
    cached:     false,
    error:      errorMessage,
  }
}
