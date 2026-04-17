import type { AgentResult } from '../interfaces/agent/agent-result.ts'

export type RunEvent =
  | { type: 'run:plan'; agentNames: string[] }
  | { type: 'agent:start'; agentName: string }
  | { type: 'agent:chunk'; agentName: string; text: string }
  | { type: 'agent:complete'; result: AgentResult }
  | { type: 'agent:error'; agentName: string; error: string }
  | { type: 'run:complete'; results: AgentResult[]; durationMs: number }
  | { type: 'run:error'; error: string }
