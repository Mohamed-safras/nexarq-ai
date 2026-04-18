import { runOrchestrator } from '@nexarq/agent-runtime'
import type { OrchestratorRunResult } from '@nexarq/agent-runtime'
import type { RunConfig, RunEvent } from '@nexarq/common/types'
import type { TriggerSource } from '@nexarq/agent-runtime'

export interface NexarqClientOptions {
  /** API key for the Nexarq web backend (optional — omit to run locally) */
  apiKey?: string
  /** Web backend URL (default: https://nexarq.dev/api) */
  baseUrl?: string
  /** Default LLM provider */
  provider?: RunConfig['provider']
  /** Default model */
  model?: string
}

export interface ReviewOptions {
  /** Git diff string to review */
  diff: string
  /** Agent names to run (default: context-selected) */
  agents?: string[]
  /** Execution mode */
  mode?: RunConfig['mode']
  /** Trigger source (default: 'sdk') */
  triggerSource?: TriggerSource
  /** Working directory for tool-augmented agents */
  workingDirectory?: string
  /** Streaming event callback */
  onEvent?: (event: RunEvent) => void
}

export interface CodeOptions {
  /** Natural language task description */
  task: string
  /** Working directory for the coding agent */
  workingDirectory?: string
  /** Streaming event callback */
  onEvent?: (event: RunEvent) => void
}

/**
 * NexarqClient — programmatic access to all Nexarq agent capabilities.
 *
 * Local mode (default): runs agents in-process using the agent-runtime.
 * Remote mode: when `apiKey` is set, proxies through the Nexarq web API.
 *
 * @example
 * ```ts
 * import { NexarqClient } from '@nexarq/sdk'
 *
 * const client = new NexarqClient({ provider: 'anthropic' })
 *
 * const result = await client.review({
 *   diff: myGitDiff,
 *   agents: ['security', 'bugs', 'performance'],
 *   mode: 'smart',
 * })
 *
 * console.log(result.summary)
 * ```
 */
export class NexarqClient {
  private readonly options: NexarqClientOptions

  constructor(options: NexarqClientOptions = {}) {
    this.options = options
  }

  async review(reviewOptions: ReviewOptions): Promise<OrchestratorRunResult> {
    return runOrchestrator({
      task: 'Review the following diff',
      diffResult: {
        rawDiff: reviewOptions.diff,
        files: [],
        totalAdded: reviewOptions.diff.split('\n').filter((line) => line.startsWith('+')).length,
        totalRemoved: reviewOptions.diff.split('\n').filter((line) => line.startsWith('-')).length,
        changeType: 'general',
        repoType: 'unknown',
        primaryLanguage: 'unknown',
      },
      triggerSource: reviewOptions.triggerSource ?? 'sdk',
      workingDirectory: reviewOptions.workingDirectory ?? process.cwd(),
      runConfig: {
        agents: reviewOptions.agents,
        mode: reviewOptions.mode ?? 'smart',
        provider: this.options.provider,
        model: this.options.model,
      },
      onEvent: reviewOptions.onEvent,
    })
  }

  async code(codeOptions: CodeOptions): Promise<OrchestratorRunResult> {
    return runOrchestrator({
      task: codeOptions.task,
      triggerSource: 'coding-agent',
      workingDirectory: codeOptions.workingDirectory ?? process.cwd(),
      runConfig: {
        provider: this.options.provider,
        model: this.options.model,
      },
      onEvent: codeOptions.onEvent,
    })
  }

  /**
   * Stream review events as an async generator — useful for real-time UIs.
   *
   * @example
   * ```ts
   * for await (const event of client.streamReview({ diff })) {
   *   if (event.type === 'agent:complete') console.log(event.result)
   * }
   * ```
   */
  async *streamReview(reviewOptions: ReviewOptions): AsyncGenerator<RunEvent> {
    const events: RunEvent[] = []
    let isDone = false
    let resolveNext: ((value: IteratorResult<RunEvent>) => void) | null = null

    const enqueue = (event: RunEvent) => {
      if (resolveNext) {
        const resolve = resolveNext
        resolveNext = null
        resolve({ value: event, done: false })
      } else {
        events.push(event)
      }
    }

    // Run in the background, enqueueing events as they arrive
    this.review({ ...reviewOptions, onEvent: enqueue }).then(() => {
      isDone = true
      if (resolveNext) {
        resolveNext({ value: undefined as unknown as RunEvent, done: true })
      }
    })

    while (true) {
      if (events.length > 0) {
        yield events.shift()!
      } else if (isDone) {
        return
      } else {
        const event = await new Promise<IteratorResult<RunEvent>>((resolve) => {
          resolveNext = resolve
        })
        if (event.done) return
        yield event.value
      }
    }
  }
}
