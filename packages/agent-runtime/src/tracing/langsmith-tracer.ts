import { traceable } from 'langsmith/traceable'
import type { NexarqGraphState } from '../graph/state.ts'
import type { TriggerSource } from '../selector.ts'

/**
 * Whether LangSmith tracing is enabled.
 * Requires LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY in env.
 * Silently no-ops when disabled — no code changes needed elsewhere.
 */
export function isTracingEnabled(): boolean {
  return (
    process.env['LANGCHAIN_TRACING_V2'] === 'true' &&
    Boolean(process.env['LANGCHAIN_API_KEY'])
  )
}

/**
 * Wraps an async function with LangSmith tracing metadata.
 * When tracing is disabled this is a transparent passthrough.
 *
 * Usage:
 *   const tracedRun = withTracing(myRunFn, { name: 'nexarq.run', triggerSource: 'post-commit' })
 *   await tracedRun(state)
 */
export function withTracing<TInput, TOutput>(
  fn: (input: TInput) => Promise<TOutput>,
  metadata: { name: string; triggerSource: TriggerSource; agentNames?: string[] }
): (input: TInput) => Promise<TOutput> {
  if (!isTracingEnabled()) return fn

  return traceable(fn as (...args: unknown[]) => unknown, {
    name: metadata.name,
    metadata: {
      triggerSource: metadata.triggerSource,
      agentNames: metadata.agentNames ?? [],
      project: process.env['LANGCHAIN_PROJECT'] ?? 'nexarq',
    },
    run_type: 'chain',
  }) as (input: TInput) => Promise<TOutput>
}

/**
 * Tags a complete orchestrator run with result metadata for LangSmith.
 * Call this after the graph finishes to attach severity counts and timing.
 */
export function buildRunMetadata(state: NexarqGraphState, durationMs: number) {
  return {
    triggerSource: state.triggerSource,
    agentsRun: state.dispatchedAgents,
    totalFindings: state.agentResults.reduce(
      (total, result) => total + result.findings.length, 0
    ),
    hasHighSeverity: state.hasHighSeverityFinding,
    tokensUsed: state.agentResults.reduce(
      (total, result) => total + result.tokenUsage.totalTokens, 0
    ),
    durationMs,
  }
}
