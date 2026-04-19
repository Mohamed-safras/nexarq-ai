import { StateGraph, END, START } from '@langchain/langgraph'
import type { NexarqGraphState, WorkflowSubtask } from './state.ts'
import { buildStateChannels } from './state.ts'

import { runReviewAgentNode } from './nodes/review-node.ts'
import { runSummaryNode } from './nodes/summary-node.ts'
import { runTriageNode } from './nodes/triage-node.ts'
import { runArchitectNode } from './nodes/workflow/architect-node.ts'
import { runCoderNode } from './nodes/workflow/coder-node.ts'
import { runTesterNode } from './nodes/workflow/tester-node.ts'
import { runReviewerNode } from './nodes/workflow/reviewer-node.ts'
import type { AgentSelectionPlan } from '../selector.ts'

// ── Review graph ─────────────────────────────────────────────────────────────

/**
 * Review graph topology:
 *   START → router → [review_agent_1 … review_agent_N in parallel] → summary → END
 */
export function buildNexarqGraph(plan: AgentSelectionPlan) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graph = new StateGraph<NexarqGraphState>({ channels: buildStateChannels() } as any) as any

  const ROUTER_NODE  = 'router'
  const TRIAGE_NODE  = 'triage'
  const SUMMARY_NODE = 'summary'

  graph.addNode(ROUTER_NODE, (state: NexarqGraphState) => state)

  const reviewNodeNames: string[] = []
  for (const agentDef of plan.allSelectedAgents) {
    const nodeName = `review_${agentDef.name}`
    reviewNodeNames.push(nodeName)
    graph.addNode(nodeName, (state: NexarqGraphState) =>
      runReviewAgentNode(state, agentDef.name)
    )
  }

  graph.addNode(TRIAGE_NODE, runTriageNode)
  graph.addNode(SUMMARY_NODE, runSummaryNode)

  graph.addEdge(START, ROUTER_NODE)
  graph.addConditionalEdges(
    ROUTER_NODE,
    (_state: NexarqGraphState): string | string[] =>
      reviewNodeNames.length > 0 ? reviewNodeNames : TRIAGE_NODE
  )
  for (const nodeName of reviewNodeNames) {
    graph.addEdge(nodeName, TRIAGE_NODE)
  }
  graph.addEdge(TRIAGE_NODE, SUMMARY_NODE)
  graph.addEdge(SUMMARY_NODE, END)

  return graph.compile()
}

// ── Coding graph ─────────────────────────────────────────────────────────────

/**
 * Coding graph topology:
 *   START → architect → [coder_1 … coder_N in parallel] → tester → reviewer → END
 *
 * Subtask count is known before this is called (planner runs pre-graph),
 * so the fan-out width is fixed at compile time.
 */
export function buildCodingGraph(subtasks: WorkflowSubtask[]) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graph = new StateGraph<NexarqGraphState>({ channels: buildStateChannels() } as any) as any

  const ARCHITECT_NODE = 'architect'
  const TESTER_NODE    = 'tester'
  const REVIEWER_NODE  = 'reviewer'

  graph.addNode(ARCHITECT_NODE, runArchitectNode)

  const coderNodeNames: string[] = []
  for (const subtask of subtasks) {
    const nodeName = `coder_${subtask.id}`
    coderNodeNames.push(nodeName)
    graph.addNode(nodeName, (state: NexarqGraphState) => runCoderNode(state, subtask))
  }

  graph.addNode(TESTER_NODE, runTesterNode)
  graph.addNode(REVIEWER_NODE, runReviewerNode)

  graph.addEdge(START, ARCHITECT_NODE)
  graph.addConditionalEdges(
    ARCHITECT_NODE,
    (): string[] => coderNodeNames.length > 0 ? coderNodeNames : [TESTER_NODE]
  )
  for (const nodeName of coderNodeNames) {
    graph.addEdge(nodeName, TESTER_NODE)
  }
  graph.addEdge(TESTER_NODE, REVIEWER_NODE)
  graph.addEdge(REVIEWER_NODE, END)

  return graph.compile()
}
