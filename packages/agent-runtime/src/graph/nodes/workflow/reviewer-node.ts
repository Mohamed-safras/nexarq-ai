import type { NexarqGraphState } from '../../state.ts'
import { streamAgentOutput, fireComplete } from './node-utils.ts'

const SYSTEM_PROMPT = `You are the Reviewer Agent — the final synthesizer in a parallel AI coding system.

Your role: Read all agent outputs and write a clear, concise final report for the developer.

The report should cover:
- What was built (a brief summary of implemented features)
- Which files were changed
- Test results
- Any issues, warnings, or follow-up items the developer should know about
- Next steps if further work is needed

Be concise and developer-friendly. No padding.`

function buildPrompt(
  task: string,
  planSummary: string,
  architectOutput: string,
  coderOutputs: string,
  testerOutput: string,
  modifiedFiles: string[]
): string {
  const files = modifiedFiles.length > 0
    ? modifiedFiles.map((f) => `  - ${f}`).join('\n')
    : '  (none recorded)'

  return `Original task: ${task}

Plan: ${planSummary}

Architecture decisions:
${architectOutput}

Coder outputs:
${coderOutputs}

Test results:
${testerOutput}

Modified files:
${files}

Write the final report.`
}

export async function runReviewerNode(
  state: NexarqGraphState
): Promise<Partial<NexarqGraphState>> {
  const agentName   = 'reviewer'
  state.onEvent?.({ type: 'agent:start', agentName })

  const coderOutputs = state.coderResults
    .map((r) => `[Subtask ${r.subtaskId}]\n${r.output}`)
    .join('\n\n---\n\n')

  const startTime = Date.now()

  try {
    const output = await streamAgentOutput(
      state.runConfig,
      SYSTEM_PROMPT,
      buildPrompt(
        state.task,
        state.planSummary,
        state.architectOutput,
        coderOutputs,
        state.testerOutput,
        state.modifiedFiles
      ),
      agentName,
      state.onEvent,
      { temperature: 0.1, maxTokens: 2048 }
    )
    fireComplete(state.onEvent, agentName, output, Date.now() - startTime)
    return { reviewerOutput: output, isDone: true }
  } catch (err) {
    const error = err instanceof Error ? err.message : String(err)
    state.onEvent?.({ type: 'agent:error', agentName, error })
    return { reviewerOutput: '', isDone: true, errorMessage: error }
  }
}
