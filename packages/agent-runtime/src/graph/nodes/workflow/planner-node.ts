import type { BaseMessage } from '@langchain/core/messages'
import { HumanMessage, SystemMessage } from '@langchain/core/messages'
import { createReactAgent } from '@langchain/langgraph/prebuilt'
import type { WorkflowSubtask } from '../../state.ts'
import { getReadTools } from '../../../tools/index.ts'
import type { RunConfig } from '@nexarq/common/interfaces'
import type { RunEvent } from '@nexarq/common/types'
import { buildChatModel, fireComplete } from './node-utils.ts'

const SYSTEM_PROMPT = `You are the Planning Agent in a parallel AI coding system.

Your role: Explore the codebase to fully understand the task, then produce a parallelizable implementation plan.

Use your read tools to:
1. Understand the project structure and conventions
2. Find relevant existing code
3. Determine what needs to be built or changed

Then output a plan as a JSON block (the ONLY JSON in your response) wrapped in triple backticks:
\`\`\`json
{
  "summary": "one-sentence description of the overall approach",
  "subtasks": [
    {
      "id": "1",
      "title": "Short action title",
      "description": "Detailed description of exactly what to implement",
      "targetFiles": ["relative/path/to/file.ts"]
    }
  ]
}
\`\`\`

Rules:
- 2–4 subtasks only — more creates coordination overhead
- Each subtask must be independently executable (no subtask depends on another's code output)
- Be specific about files — use actual paths from the project you've explored`

function buildPrompt(task: string, knowledgeContext?: string): string {
  const ctx = knowledgeContext ? `\n\nProject knowledge:\n${knowledgeContext}` : ''
  return `Task: ${task}${ctx}\n\nExplore the codebase, then output your implementation plan as JSON.`
}

export interface PlannerResult {
  subtasks: WorkflowSubtask[]
  planSummary: string
}

/**
 * Runs the planner agent BEFORE the workflow graph is built so the orchestrator
 * knows how many coder nodes to create.
 */
export async function runPlannerAgent(
  task: string,
  runConfig: RunConfig,
  workingDirectory: string,
  knowledgeContext: string | undefined,
  onEvent?: (event: RunEvent) => void
): Promise<PlannerResult> {
  const agentName = 'planner'
  onEvent?.({ type: 'agent:start', agentName })

  const chatModel = buildChatModel(runConfig, { temperature: 0.2, maxTokens: 4096 })
  const tools     = getReadTools(workingDirectory)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const agent     = createReactAgent({ llm: chatModel as any, tools })

  const startTime = Date.now()

  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const result = await (agent as any).invoke(
      {
        messages: [
          new SystemMessage(SYSTEM_PROMPT),
          new HumanMessage(buildPrompt(task, knowledgeContext)),
        ],
      },
      { recursionLimit: 100 }
    ) as { messages: BaseMessage[] }

    const lastMsg  = result.messages.at(-1)
    const rawOutput = lastMsg ? String(lastMsg.content) : ''
    const parsed   = parsePlan(rawOutput)

    fireComplete(onEvent, agentName, rawOutput, Date.now() - startTime)
    return parsed
  } catch (err) {
    const error = err instanceof Error ? err.message : String(err)
    onEvent?.({ type: 'agent:error', agentName, error })
    return {
      subtasks: [{ id: '1', title: task, description: task }],
      planSummary: task,
    }
  }
}

function parsePlan(raw: string): PlannerResult {
  const jsonMatch = raw.match(/```json\s*([\s\S]*?)```/)
  if (!jsonMatch) {
    return {
      subtasks: [{ id: '1', title: 'Implement task', description: raw.slice(0, 500) }],
      planSummary: raw.slice(0, 200),
    }
  }

  try {
    const parsed = JSON.parse(jsonMatch[1] ?? '{}') as {
      summary?: string
      subtasks: Array<{ id: string; title: string; description: string; targetFiles?: string[] }>
    }
    return {
      subtasks: (parsed.subtasks ?? []).slice(0, 4),
      planSummary: parsed.summary ?? '',
    }
  } catch {
    return {
      subtasks: [{ id: '1', title: 'Implement task', description: raw.slice(0, 500) }],
      planSummary: raw.slice(0, 200),
    }
  }
}
