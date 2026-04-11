import { StateGraph, END, START } from '@langchain/langgraph'
import type { NexarqGraphState } from './state.ts'
import { GRAPH_STATE_DEFAULTS } from './state.ts'
import { runReviewAgentNode } from './nodes/review-node.ts'
import { runCodingAgentNode } from './nodes/coding-agent-node.ts'
import { runSummaryNode } from './nodes/summary-node.ts'
import type { AgentSelectionPlan } from '../selector.ts'

const ROUTER_NODE = 'router'
const CODING_AGENT_NODE = 'coding_agent'
const SUMMARY_NODE = 'summary'

/**
 * Builds and compiles the Nexarq LangGraph graph.
 *
 * Graph topology:
 *
 *   START → router ─┬─(coding-agent)──→ coding_agent → END
 *                   └─(review)─→ [agent nodes in parallel] → summary → END
 *
 * The graph is the same regardless of trigger source — the router node
 * reads `triggerSource` from state and directs to the correct path.
 */
export function buildNexarqGraph(plan: AgentSelectionPlan) {
  const graph = new StateGraph<NexarqGraphState>({
    channels: buildStateChannels(),
  })

  // Router — decides which path to take
  graph.addNode(ROUTER_NODE, (state: NexarqGraphState) => state)

  // Coding-agent path
  graph.addNode(CODING_AGENT_NODE, runCodingAgentNode)

  // Review-agent nodes — one node per selected agent
  const reviewNodeNames: string[] = []
  for (const agentDef of plan.allSelectedAgents) {
    const nodeName = `review_${agentDef.name}`
    reviewNodeNames.push(nodeName)
    graph.addNode(nodeName, (state: NexarqGraphState) =>
      runReviewAgentNode(state, agentDef.name)
    )
  }

  // Summary node — assembles all review results
  graph.addNode(SUMMARY_NODE, runSummaryNode)

  // Edges
  graph.addEdge(START, ROUTER_NODE)

  graph.addConditionalEdges(
    ROUTER_NODE,
    routeByTrigger,
    {
      coding_agent: CODING_AGENT_NODE,
      review: reviewNodeNames.length > 0 ? reviewNodeNames[0]! : SUMMARY_NODE,
    }
  )

  // Fan-out: all review nodes run, then converge at summary
  for (const nodeName of reviewNodeNames) {
    graph.addEdge(nodeName, SUMMARY_NODE)
  }

  graph.addEdge(CODING_AGENT_NODE, END)
  graph.addEdge(SUMMARY_NODE, END)

  return graph.compile()
}

function routeByTrigger(state: NexarqGraphState): 'coding_agent' | 'review' {
  return state.triggerSource === 'coding-agent' ? 'coding_agent' : 'review'
}

function buildStateChannels(): Record<string, unknown> {
  // LangGraph channel definition — each key maps to a reducer or default value.
  // Arrays use append-reducer; primitives use last-write-wins.
  return {
    task:                   { default: () => '' },
    triggerSource:          { default: () => 'on-demand' },
    diffResult:             { default: () => undefined },
    runConfig:              { default: () => ({}) },
    messages:               { reducer: (existing: unknown[], incoming: unknown[]) => [...existing, ...incoming], default: () => [] },
    dispatchedAgents:       { reducer: (existing: string[], incoming: string[]) => [...existing, ...incoming], default: () => [] },
    agentResults:           { reducer: (existing: unknown[], incoming: unknown[]) => [...existing, ...incoming], default: () => [] },
    hasHighSeverityFinding: { default: () => false },
    toolCallCount:          { default: () => 0 },
    workingDirectory:       { default: () => undefined },
    modifiedFiles:          { reducer: (existing: string[], incoming: string[]) => [...existing, ...incoming], default: () => [] },
    finalOutput:            { default: () => '' },
    isDone:                 { default: () => false },
    errorMessage:           { default: () => undefined },
    ...Object.fromEntries(
      Object.entries(GRAPH_STATE_DEFAULTS).map(([key]) => [key, {}])
    ),
  }
}
