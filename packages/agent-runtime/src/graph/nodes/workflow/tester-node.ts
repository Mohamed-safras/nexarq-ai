import type { NexarqGraphState, WorkflowCoderResult } from '../../state.ts'
import { getReadTools, getWriteTools } from '../../../tools/index.ts'
import { runReactAgent, fireComplete } from './node-utils.ts'

const SYSTEM_PROMPT = `You are the Testing Agent in a parallel AI coding system.

Your role: Write and run tests for the code implemented by coder agents.

Your workflow:
1. READ — examine the modified files and understand what was implemented
2. WRITE TESTS — create test files for the new code
3. RUN TESTS — execute the test suite using the run_command tool
4. FIX — if tests fail, fix the implementation or tests
5. REPORT — summarize what you tested and the results

Use the run_command tool to run: bun test, npm test, jest, vitest, pytest, go test, etc.
Focus on testing the behaviour that was just implemented — don't rewrite existing tests.`

function buildPrompt(coderResults: WorkflowCoderResult[], modifiedFiles: string[]): string {
  const fileList = modifiedFiles.length > 0 ? modifiedFiles.join('\n  - ') : '(see coder summaries below)'
  const coderSummaries = coderResults
    .filter((r) => !r.error && r.output)
    .map((r) => `Subtask ${r.subtaskId}:\n${r.output}`)
    .join('\n\n---\n\n')

  return `Modified files:\n  - ${fileList}\n\nCoder agent summaries:\n${coderSummaries}\n\nWrite and run tests for these changes. Report results.`
}

export async function runTesterNode(
  state: NexarqGraphState
): Promise<Partial<NexarqGraphState>> {
  const agentName = 'tester'
  state.onEvent?.({ type: 'agent:start', agentName })

  const wd    = state.workingDirectory ?? process.cwd()
  const tools = [...getReadTools(wd), ...getWriteTools(wd)]
  const startTime = Date.now()

  try {
    const output = await runReactAgent(
      state.runConfig,
      SYSTEM_PROMPT,
      buildPrompt(state.coderResults, state.modifiedFiles),
      tools,
      { temperature: 0.2, maxTokens: 4096 }
    )
    fireComplete(state.onEvent, agentName, output, Date.now() - startTime)
    return { testerOutput: output }
  } catch (err) {
    const error = err instanceof Error ? err.message : String(err)
    state.onEvent?.({ type: 'agent:error', agentName, error })
    return { testerOutput: `Testing failed: ${error}` }
  }
}
