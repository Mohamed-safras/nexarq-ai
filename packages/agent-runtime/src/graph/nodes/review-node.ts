import { HumanMessage, SystemMessage } from '@langchain/core/messages'
import { isHighPriority } from '@nexarq/common/utils'
import type { AgentResult } from '@nexarq/common/types'
import type { NexarqGraphState } from '../state.ts'
import { getAgent } from '../../registry.ts'
import { getProvider } from '../../providers/provider-factory.ts'
import type { ProviderName } from '@nexarq/common/types'

/**
 * Runs a single named review agent and appends its result to graph state.
 * Each review agent gets its own node invocation — LangGraph fans them out
 * in parallel via the orchestrator's parallel edges.
 */
export async function runReviewAgentNode(
  state: NexarqGraphState,
  agentName: string
): Promise<Partial<NexarqGraphState>> {
  const agentDefinition = getAgent(agentName)
  if (!agentDefinition) {
    return {
      agentResults: [
        ...state.agentResults,
        buildErrorResult(agentName, `Agent "${agentName}" not found in registry`),
      ],
    }
  }

  const diffResult = state.diffResult
  if (!diffResult) {
    return {
      agentResults: [
        ...state.agentResults,
        buildErrorResult(agentName, 'No diff result available for review agent'),
      ],
    }
  }

  const providerName = (state.runConfig.provider ?? 'ollama') as ProviderName
  const provider = getProvider(providerName)
  const chatModel = provider.buildModel({
    model: state.runConfig.model,
    temperature: 0.2,
    maxTokens: 4096,
  })

  const userPrompt = agentDefinition.buildPrompt(
    diffResult.rawDiff,
    diffResult.primaryLanguage
  )

  const startTime = Date.now()

  try {
    const response = await (chatModel as { invoke: (msgs: unknown[]) => Promise<{ content: string }> }).invoke([
      new SystemMessage(agentDefinition.systemPrompt),
      new HumanMessage(userPrompt),
    ])

    const agentResult: AgentResult = {
      agentName,
      severity: agentDefinition.severity,
      output: response.content,
      findings: [],
      warnings: [],
      tokenUsage: { promptTokens: 0, completionTokens: 0, totalTokens: 0 },
      latencyMs: Date.now() - startTime,
      cached: false,
    }

    const updatedResults = [...state.agentResults, agentResult]
    const hasHighSeverity = updatedResults.some((result) => isHighPriority(result.severity))

    return {
      agentResults: updatedResults,
      dispatchedAgents: [...state.dispatchedAgents, agentName],
      hasHighSeverityFinding: hasHighSeverity,
    }
  } catch (caughtError) {
    const errorMessage = caughtError instanceof Error ? caughtError.message : String(caughtError)
    return {
      agentResults: [
        ...state.agentResults,
        buildErrorResult(agentName, errorMessage),
      ],
      dispatchedAgents: [...state.dispatchedAgents, agentName],
    }
  }
}

function buildErrorResult(agentName: string, errorMessage: string): AgentResult {
  return {
    agentName,
    severity: 'info',
    output: '',
    findings: [],
    warnings: [],
    tokenUsage: { promptTokens: 0, completionTokens: 0, totalTokens: 0 },
    latencyMs: 0,
    cached: false,
    error: errorMessage,
  }
}
