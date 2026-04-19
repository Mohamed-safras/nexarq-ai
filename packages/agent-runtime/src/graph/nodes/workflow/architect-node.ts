import type { NexarqGraphState, WorkflowSubtask } from '../../state.ts'
import { getReadTools } from '../../../tools/index.ts'
import { runReactAgent, fireComplete } from './node-utils.ts'

const SYSTEM_PROMPT = `You are the Architecture Agent in a parallel AI coding system.

Your role: Explore the codebase and design a clear technical architecture for the implementation plan.

You have read-only tools to explore the existing code. Use them to:
1. Understand the current project structure, patterns, and conventions
2. Identify which files need to be created or modified
3. Define the interfaces and data contracts between subtasks

Output a concise architecture document covering:
- Technology choices and patterns to follow
- File structure changes needed
- Interfaces / types / contracts each coder agent must implement
- Shared utilities or dependencies to be aware of

Be specific and actionable — coder agents will use this as their implementation guide.`

function buildPrompt(task: string, subtasks: WorkflowSubtask[], knowledgeContext?: string): string {
  const subtaskList = subtasks.map((s) => `  ${s.id}. ${s.title}: ${s.description}`).join('\n')
  const ctx = knowledgeContext ? `\n\nProject knowledge:\n${knowledgeContext}` : ''
  return `Task: ${task}

Planned subtasks (each will be implemented by a parallel coder agent):
${subtaskList}
${ctx}

Explore the codebase, then produce the architecture document.`
}

export async function runArchitectNode(
  state: NexarqGraphState
): Promise<Partial<NexarqGraphState>> {
  const agentName = 'architect'
  state.onEvent?.({ type: 'agent:start', agentName })

  const startTime = Date.now()
  try {
    const output = await runReactAgent(
      state.runConfig,
      SYSTEM_PROMPT,
      buildPrompt(state.task, state.subtasks, state.knowledgeContext),
      getReadTools(state.workingDirectory ?? process.cwd()),
      { temperature: 0.2, maxTokens: 4096 }
    )
    fireComplete(state.onEvent, agentName, output, Date.now() - startTime)
    return { architectOutput: output }
  } catch (err) {
    const error = err instanceof Error ? err.message : String(err)
    state.onEvent?.({ type: 'agent:error', agentName, error })
    return { architectOutput: '', errorMessage: error }
  }
}
