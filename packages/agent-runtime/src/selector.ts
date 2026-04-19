import type { AgentMode } from '@nexarq/common/types'
import type { DiffResult } from '@nexarq/common/interfaces'
import type { AgentDefinition } from '@nexarq/common/interfaces'
import { DEFAULT_TIER1_AGENTS, DEFAULT_MAX_AGENTS } from '@nexarq/common/constants'
import { getAllAgents, getAgentsByTier } from './registry.ts'

/**
 * Where this agent run was triggered from.
 * The selector uses this to decide which agents run and how strictly.
 *
 * Review triggers (diff-based):
 *   post-commit  — local git hook after every commit
 *   pre-push     — blocks push on CRITICAL/HIGH; must be fast
 *   pr-review    — full review from a GitHub PR webhook
 *   on-demand    — developer ran `nexarq run` manually
 *   scheduled    — nightly/weekly cron run from the web dashboard
 *
 * Programmatic:
 *   sdk          — called via @nexarq/sdk from any integration
 */
export type TriggerSource =
  | 'post-commit'
  | 'pre-push'
  | 'pr-review'
  | 'on-demand'
  | 'scheduled'
  | 'sdk'

export interface AgentSelectionContext {
  diffResult?: DiffResult
  mode: AgentMode
  triggerSource: TriggerSource
  requestedAgentNames?: string[]
  maxAgents?: number
}

export interface AgentSelectionPlan {
  priorityAgents: AgentDefinition[]
  parallelAgents: AgentDefinition[]
  allSelectedAgents: AgentDefinition[]
  triggerSource: TriggerSource
}

export function selectAgents(context: AgentSelectionContext): AgentSelectionPlan {
  const {
    diffResult,
    mode,
    triggerSource,
    requestedAgentNames,
    maxAgents = DEFAULT_MAX_AGENTS,
  } = context

  // Explicit agent list — honour it regardless of trigger or mode
  if (requestedAgentNames && requestedAgentNames.length > 0) {
    const matchedAgents = getAllAgents().filter((agentDef) =>
      requestedAgentNames.includes(agentDef.name)
    )
    return buildPlan(matchedAgents, [], maxAgents, triggerSource)
  }

  const tier1Agents = getAgentsByTier(1)

  // pre-push: tier 1 only — must not block the developer for long
  if (triggerSource === 'pre-push' || mode === 'fast') {
    return buildPlan(tier1Agents, [], maxAgents, triggerSource)
  }

  // scheduled / pr-review / deep: run all agents
  if (triggerSource === 'scheduled' || triggerSource === 'pr-review' || mode === 'deep') {
    const deeperAgents = getAllAgents().filter((agentDef) => agentDef.tier !== 1)
    return buildPlan(tier1Agents, deeperAgents, maxAgents, triggerSource)
  }

  // post-commit / on-demand / sdk / smart / auto — derive from diff context
  const contextualAgents = diffResult
    ? deriveAgentsFromDiff(diffResult)
    : getAllAgents().filter((agentDef) => agentDef.tier === 2)

  return buildPlan(tier1Agents, contextualAgents, maxAgents, triggerSource)
}

function buildPlan(
  priorityAgents: AgentDefinition[],
  candidateParallelAgents: AgentDefinition[],
  maxAgents: number,
  triggerSource: TriggerSource,
): AgentSelectionPlan {
  const priorityNameSet = new Set(priorityAgents.map((agentDef) => agentDef.name))
  const deduplicatedParallel = candidateParallelAgents.filter(
    (agentDef) => !priorityNameSet.has(agentDef.name)
  )

  const allSelected = [...priorityAgents, ...deduplicatedParallel].slice(0, maxAgents)
  const finalPriority = allSelected.filter((agentDef) => priorityNameSet.has(agentDef.name))
  const finalParallel = allSelected.filter((agentDef) => !priorityNameSet.has(agentDef.name))

  return { priorityAgents: finalPriority, parallelAgents: finalParallel, allSelectedAgents: allSelected, triggerSource }
}

/**
 * Selects agents based on diff content by reading each agent's selectionHints.
 * Agents are self-describing — no hardcoded dispatch map here.
 */
function deriveAgentsFromDiff(diffResult: DiffResult): AgentDefinition[] {
  const allAgents    = getAllAgents()
  const selectedNames = new Set<string>(DEFAULT_TIER1_AGENTS)
  const { changeType, files, rawDiff, totalAdded, totalRemoved } = diffResult
  const rawDiffLower = rawDiff.toLowerCase()
  const filePaths    = files.map((f) => f.path.toLowerCase())
  const diffLines    = totalAdded + totalRemoved

  for (const agent of allAgents) {
    const hints = agent.selectionHints
    if (!hints) continue

    if (hints.changeTypes?.includes(changeType)) {
      selectedNames.add(agent.name)
      continue
    }
    if (hints.filePaths?.some((fp) => filePaths.some((p) => p.includes(fp)))) {
      selectedNames.add(agent.name)
      continue
    }
    if (hints.diffContent?.some((kw) => rawDiffLower.includes(kw))) {
      selectedNames.add(agent.name)
      continue
    }
    if (hints.minDiffLines !== undefined && diffLines >= hints.minDiffLines) {
      selectedNames.add(agent.name)
    }
  }

  return allAgents.filter((agentDef) => selectedNames.has(agentDef.name))
}
