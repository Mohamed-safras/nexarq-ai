import { createReactAgent } from '@langchain/langgraph/prebuilt'
import { HumanMessage, SystemMessage } from '@langchain/core/messages'
import { getProvider } from '../../../providers/provider-factory.ts'
import type { RunConfig } from '@nexarq/common/interfaces'
import type { RunEvent, ProviderName } from '@nexarq/common/types'

export interface AgentModelOptions {
  temperature?: number
  maxTokens?: number
}

/** Builds a chat model from RunConfig with optional overrides. */
export function buildChatModel(runConfig: RunConfig, opts: AgentModelOptions = {}) {
  const providerName = (runConfig.provider ?? 'ollama') as ProviderName
  const provider = getProvider(providerName)
  return provider.buildModel({
    ...(runConfig.model ? { model: runConfig.model } : {}),
    temperature: opts.temperature ?? 0.2,
    maxTokens:   opts.maxTokens ?? 4096,
  })
}

/**
 * Runs a ReAct agent with the given system prompt, user prompt, and tools.
 * Returns the final text output from the last message.
 */
export async function runReactAgent(
  runConfig: RunConfig,
  systemPrompt: string,
  userPrompt: string,
  tools: unknown[],
  modelOpts: AgentModelOptions = {}
): Promise<string> {
  const chatModel = buildChatModel(runConfig, modelOpts)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const agent = createReactAgent({ llm: chatModel as any, tools: tools as any[] })

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const result = await (agent as any).invoke(
    {
      messages: [
        new SystemMessage(systemPrompt),
        new HumanMessage(userPrompt),
      ],
    },
    { recursionLimit: 100 }
  ) as { messages: Array<{ content: unknown }> }

  const lastMsg = result.messages.at(-1)
  return lastMsg ? String(lastMsg.content) : ''
}

/**
 * Streams a non-tool LLM call and collects the output.
 * Fires agent:chunk events as text arrives.
 */
export async function streamAgentOutput(
  runConfig: RunConfig,
  systemPrompt: string,
  userPrompt: string,
  agentName: string,
  onEvent: ((event: RunEvent) => void) | undefined,
  modelOpts: AgentModelOptions = {}
): Promise<string> {
  const chatModel = buildChatModel(runConfig, modelOpts)

  type StreamModel = {
    stream: (msgs: unknown[]) => Promise<AsyncIterable<{ content: unknown }>>
  }
  const stream = await (chatModel as StreamModel).stream([
    new SystemMessage(systemPrompt),
    new HumanMessage(userPrompt),
  ])

  let output = ''
  for await (const chunk of stream) {
    const text = typeof chunk.content === 'string' ? chunk.content : ''
    output += text
    if (text) onEvent?.({ type: 'agent:chunk', agentName, text })
  }
  return output
}

/**
 * Runs a ReAct agent with Claude extended thinking enabled.
 * Extended thinking lets Claude reason privately before each tool call,
 * enabling deeper multi-hop analysis (e.g. trace an auth flow then look up CVEs).
 *
 * Falls back to standard runReactAgent when the active provider is not Anthropic,
 * since extended thinking is a Claude-only feature.
 */
export async function runThinkingAgent(
  runConfig: RunConfig,
  systemPrompt: string,
  userPrompt: string,
  tools: unknown[],
  modelOpts: AgentModelOptions = {}
): Promise<string> {
  const providerName = (runConfig.provider ?? 'ollama') as ProviderName
  if (providerName !== 'anthropic') {
    return runReactAgent(runConfig, systemPrompt, userPrompt, tools, modelOpts)
  }

  const { ChatAnthropic } = await import('@langchain/anthropic')
  const budgetTokens = 8_000
  const maxTokens = Math.max((modelOpts.maxTokens ?? 0), budgetTokens + 4_000)

  const thinkingModel = new ChatAnthropic({
    model: runConfig.model ?? 'claude-sonnet-4-6',
    // Extended thinking requires temperature=1 and maxTokens > budgetTokens
    temperature: 1,
    maxTokens,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    thinking: { type: 'enabled', budget_tokens: budgetTokens } as any,
    ...(process.env['NEXARQ_ANTHROPIC_API_KEY'] ? { apiKey: process.env['NEXARQ_ANTHROPIC_API_KEY'] } : {}),
  })

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const agent = createReactAgent({ llm: thinkingModel as any, tools: tools as any[] })

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const result = await (agent as any).invoke(
    {
      messages: [
        new SystemMessage(systemPrompt),
        new HumanMessage(userPrompt),
      ],
    },
    { recursionLimit: 100 }
  ) as { messages: Array<{ content: unknown }> }

  const lastMsg = result.messages.at(-1)
  if (!lastMsg) return ''
  // Content may be an array of blocks (text + thinking); extract text blocks only
  if (Array.isArray(lastMsg.content)) {
    return lastMsg.content
      .filter((b): b is { type: string; text: string } => typeof b === 'object' && b !== null && (b as { type?: string }).type === 'text')
      .map((b) => b.text)
      .join('')
  }
  return String(lastMsg.content)
}

/** Fires agent:complete with a standard zero-cost AgentResult. */
export function fireComplete(
  onEvent: ((event: RunEvent) => void) | undefined,
  agentName: string,
  output: string,
  latencyMs: number
): void {
  onEvent?.({
    type: 'agent:complete',
    result: {
      agentName,
      severity: 'info',
      output,
      findings: [],
      warnings: [],
      tokenUsage: { promptTokens: 0, completionTokens: 0, totalTokens: 0 },
      latencyMs,
      cached: false,
    },
  })
}
