import type { NexarqGraphState, WorkflowSubtask, WorkflowCoderResult } from '../../state.ts'
import { getReadTools, getWriteTools } from '../../../tools/index.ts'
import { runReactAgent, fireComplete } from './node-utils.ts'

const SYSTEM_PROMPT = `You are a Coding Agent in a parallel AI coding system.

Your role: Implement a specific subtask autonomously using your tools.

You have full read-write access to the codebase. Your workflow:
1. READ first — explore relevant files before writing anything
2. UNDERSTAND — read the architecture doc and existing patterns
3. IMPLEMENT — write clean, minimal code that satisfies your subtask
4. VERIFY — after writing, read the file back to confirm correctness
5. REPORT — summarize exactly what you changed and why

Guidelines:
- Follow the architecture document faithfully
- Match existing code style and patterns
- Make focused, minimal changes — don't touch code outside your scope
- Never delete files unless explicitly asked
- Never run destructive commands`

function buildPrompt(subtask: WorkflowSubtask, architectOutput: string, knowledgeContext?: string): string {
  const fileHints = subtask.targetFiles?.length ? `\n\nTarget files: ${subtask.targetFiles.join(', ')}` : ''
  const ctx       = knowledgeContext ? `\n\nProject knowledge:\n${knowledgeContext}` : ''
  return `Your assigned subtask:\nTitle: ${subtask.title}\nDescription: ${subtask.description}${fileHints}\n\nArchitecture guide:\n${architectOutput}${ctx}\n\nImplement this subtask now. Report your changes when done.`
}

/**
 * Scores a coder output heuristically — higher is better.
 * Avoids an extra LLM judge call; pure string analysis.
 */
function scoreOutput(output: string): number {
  let score = 0
  // Rewards
  score += (output.match(/write_file|str_replace|Written|Edited/g) ?? []).length * 3
  score += (output.match(/import|export|function|class|const /g) ?? []).length
  score += output.includes('test') || output.includes('spec') ? 5 : 0
  // Penalties
  score -= (output.match(/error|Error|failed|undefined|cannot|TODO/gi) ?? []).length * 2
  score -= output.length < 200 ? 10 : 0 // suspiciously short
  return score
}

export async function runCoderNode(
  state: NexarqGraphState,
  subtask: WorkflowSubtask
): Promise<Partial<NexarqGraphState>> {
  const agentName = `coder-${subtask.id}`
  state.onEvent?.({ type: 'agent:start', agentName })

  const workingDirectory = state.workingDirectory ?? process.cwd()
  const tools   = [...getReadTools(workingDirectory), ...getWriteTools(workingDirectory, state.onBeforeWrite)]
  const prompt  = buildPrompt(subtask, state.architectOutput, state.knowledgeContext)
  const mode    = state.runConfig.mode ?? 'smart'
  const startTime = Date.now()

  try {
    // Best-of-2 in deep mode: run twice with different temperatures, keep the better output.
    // Reuses runReactAgent — no extra infrastructure needed.
    // Token cost: ~2× but quality gain is significant for complex subtasks.
    const candidates =
      mode === 'deep'
        ? await Promise.all([
            runReactAgent(state.runConfig, SYSTEM_PROMPT, prompt, tools, { temperature: 0.2, maxTokens: 8192 }),
            runReactAgent(state.runConfig, SYSTEM_PROMPT, prompt, tools, { temperature: 0.5, maxTokens: 8192 }),
          ])
        : [await runReactAgent(state.runConfig, SYSTEM_PROMPT, prompt, tools, { temperature: 0.3, maxTokens: 8192 })]

    const output = candidates.reduce((best, candidate) =>
      scoreOutput(candidate) >= scoreOutput(best) ? candidate : best
    )

    const coderResult: WorkflowCoderResult = {
      subtaskId:     subtask.id,
      output,
      modifiedFiles: [],
    }

    fireComplete(state.onEvent, agentName, output, Date.now() - startTime)
    return { coderResults: [coderResult] }
  } catch (err) {
    const error = err instanceof Error ? err.message : String(err)
    state.onEvent?.({ type: 'agent:error', agentName, error })
    return {
      coderResults: [{ subtaskId: subtask.id, output: '', modifiedFiles: [], error }],
    }
  }
}
