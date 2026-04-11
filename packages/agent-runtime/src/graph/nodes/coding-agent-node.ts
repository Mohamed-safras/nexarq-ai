import { HumanMessage, SystemMessage } from '@langchain/core/messages'
import { createReactAgent } from '@langchain/langgraph/prebuilt'
import type { NexarqGraphState } from '../state.ts'
import { getProvider } from '../../providers/provider-factory.ts'
import { getReviewTools, getCodingTools } from '../../tools/index.ts'
import type { ProviderName } from '@nexarq/common/types'

const CODING_AGENT_SYSTEM_PROMPT = `You are Nexarq Coder, an autonomous coding assistant.

You have access to tools for reading and writing files, searching code, running safe terminal commands, and browsing the repository structure.

Guidelines:
- Understand the codebase first before making changes (read files, search code)
- Plan your approach before writing any file
- Make focused, minimal changes that solve the task
- After each write, verify the change is correct
- Never delete files unless explicitly asked
- Never run destructive or irreversible commands
- Ask for clarification via your output if the task is ambiguous

When done, summarize exactly what you changed and why.`

/**
 * The autonomous coding-agent node.
 * Uses LangGraph's createReactAgent (pre-built ReAct loop) with both
 * read-only and read-write tools, running until the task is complete
 * or the tool-call budget is exhausted.
 */
export async function runCodingAgentNode(
  state: NexarqGraphState
): Promise<Partial<NexarqGraphState>> {
  const providerName = (state.runConfig.provider ?? 'ollama') as ProviderName
  const provider = getProvider(providerName)
  const chatModel = provider.buildModel({
    model: state.runConfig.model,
    temperature: 0.3,
    maxTokens: 8192,
  })

  const allTools = [
    ...getReviewTools(state.workingDirectory ?? process.cwd()),
    ...getCodingTools(state.workingDirectory ?? process.cwd()),
  ]

  const reactAgent = createReactAgent({
    llm: chatModel,
    tools: allTools,
  })

  try {
    const agentResult = await reactAgent.invoke({
      messages: [
        new SystemMessage(CODING_AGENT_SYSTEM_PROMPT),
        new HumanMessage(state.task),
      ],
    })

    const lastMessage = agentResult.messages.at(-1)
    const outputText = lastMessage ? String(lastMessage.content) : 'Task completed.'

    return {
      messages: agentResult.messages,
      finalOutput: outputText,
      isDone: true,
    }
  } catch (caughtError) {
    const errorMessage = caughtError instanceof Error ? caughtError.message : String(caughtError)
    return {
      finalOutput: '',
      isDone: true,
      errorMessage,
    }
  }
}
