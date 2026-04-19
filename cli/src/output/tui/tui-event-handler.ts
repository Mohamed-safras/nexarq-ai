import type { RunEvent } from '@nexarq/common/types'
import type { RunTUI } from './run-tui.ts'

export interface TuiEventState {
  totalAgents: number
  doneAgents: number
}

/**
 * Shared RunEvent → RunTUI wiring used by both run-command and code-command.
 * Returns a handler function and a mutable state object so callers can read
 * the final counts after the run completes.
 */
export function createTuiEventHandler(tui: RunTUI): {
  state: TuiEventState
  onEvent: (event: RunEvent) => void
} {
  const state: TuiEventState = { totalAgents: 0, doneAgents: 0 }

  function onEvent(event: RunEvent): void {
    if (event.type === 'run:plan') {
      state.totalAgents = event.agentNames.length
      tui.initAgents(event.agentNames)
    }
    if (event.type === 'agent:start') {
      tui.setAgentStatus(event.agentName, 'running')
    }
    if (event.type === 'agent:chunk') {
      tui.appendChunk(event.agentName, event.text)
    }
    if (event.type === 'agent:complete') {
      state.doneAgents++
      tui.setAgentStatus(event.result.agentName, event.result.error ? 'error' : 'done')
      const lines = event.result.output.trim().split('\n').filter(Boolean)
      if (lines.length > 0) {
        tui.addFinding(event.result.agentName, event.result.severity, lines)
      }
      tui.updateFooter(state.doneAgents, state.totalAgents, {}, 0)
    }
    if (event.type === 'agent:error') {
      tui.setAgentStatus(event.agentName, 'error')
    }
  }

  return { state, onEvent }
}
