import type { DiffResult, AgentMode } from '@nexarq/common/types'
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
 * Coding-agent triggers (task-based, no diff required):
 *   coding-agent — autonomous task execution via `nexarq code`
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
  | 'coding-agent'
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
  isCodingAgentMode: boolean
}

export function selectAgents(context: AgentSelectionContext): AgentSelectionPlan {
  const {
    diffResult,
    mode,
    triggerSource,
    requestedAgentNames,
    maxAgents = DEFAULT_MAX_AGENTS,
  } = context

  const isCodingAgentMode = triggerSource === 'coding-agent'

  // Coding-agent mode — no review agents, uses autonomous graph path
  if (isCodingAgentMode) {
    return {
      priorityAgents: [],
      parallelAgents: [],
      allSelectedAgents: [],
      triggerSource,
      isCodingAgentMode: true,
    }
  }

  // Explicit agent list — honour it regardless of trigger or mode
  if (requestedAgentNames && requestedAgentNames.length > 0) {
    const matchedAgents = getAllAgents().filter((agentDef) =>
      requestedAgentNames.includes(agentDef.name)
    )
    return buildPlan(matchedAgents, [], maxAgents, triggerSource, false)
  }

  const tier1Agents = getAgentsByTier(1)

  // pre-push: tier 1 only — must not block the developer for long
  if (triggerSource === 'pre-push' || mode === 'fast') {
    return buildPlan(tier1Agents, [], maxAgents, triggerSource, false)
  }

  // scheduled / pr-review / deep: run all agents
  if (triggerSource === 'scheduled' || triggerSource === 'pr-review' || mode === 'deep') {
    const deeperAgents = getAllAgents().filter((agentDef) => agentDef.tier !== 1)
    return buildPlan(tier1Agents, deeperAgents, maxAgents, triggerSource, false)
  }

  // post-commit / on-demand / sdk / smart / auto — derive from diff context
  const contextualAgents = diffResult
    ? deriveAgentsFromDiff(diffResult)
    : getAllAgents().filter((agentDef) => agentDef.tier === 2)

  return buildPlan(tier1Agents, contextualAgents, maxAgents, triggerSource, false)
}

function buildPlan(
  priorityAgents: AgentDefinition[],
  candidateParallelAgents: AgentDefinition[],
  maxAgents: number,
  triggerSource: TriggerSource,
  isCodingAgentMode: boolean
): AgentSelectionPlan {
  const priorityNameSet = new Set(priorityAgents.map((agentDef) => agentDef.name))
  const deduplicatedParallel = candidateParallelAgents.filter(
    (agentDef) => !priorityNameSet.has(agentDef.name)
  )

  const allSelected = [...priorityAgents, ...deduplicatedParallel].slice(0, maxAgents)
  const finalPriority = allSelected.filter((agentDef) => priorityNameSet.has(agentDef.name))
  const finalParallel = allSelected.filter((agentDef) => !priorityNameSet.has(agentDef.name))

  return { priorityAgents: finalPriority, parallelAgents: finalParallel, allSelectedAgents: allSelected, triggerSource, isCodingAgentMode }
}

function deriveAgentsFromDiff(diffResult: DiffResult): AgentDefinition[] {
  const allAgents = getAllAgents()
  const selectedNames = new Set<string>(DEFAULT_TIER1_AGENTS)
  const { changeType, files, rawDiff, totalAdded, totalRemoved } = diffResult
  const rawDiffLower = rawDiff.toLowerCase()
  const filePaths = files.map((fileDiff) => fileDiff.path.toLowerCase())

  const changeTypeAgentMap: Partial<Record<typeof changeType, string[]>> = {
    security:    ['compliance'],
    bugfix:      ['error_handling', 'memory_safety'],
    feature:     ['review', 'test_coverage', 'docstring', 'type_safety'],
    refactor:    ['code_smells', 'maintainability', 'refactor'],
    performance: ['performance', 'resource_usage'],
    database:    ['database', 'security'],
    docs:        ['docstring', 'accessibility'],
    test:        ['test_coverage'],
  }
  const agentsForChangeType = changeTypeAgentMap[changeType] ?? []
  agentsForChangeType.forEach((agentName) => selectedNames.add(agentName))

  const pathPatterns: Array<{ keywords: string[]; agents: string[] }> = [
    { keywords: ['auth', 'security', 'crypto', 'password', 'token'], agents: ['security', 'compliance'] },
    { keywords: ['migration', 'schema', 'query', 'model'],           agents: ['database'] },
    { keywords: ['dockerfile', '.github', '/ci/', '.tf', 'k8s'],     agents: ['devops', 'dependency'] },
    { keywords: ['.test.', '.spec.', '__tests__', '/test/'],         agents: ['test_coverage'] },
    { keywords: ['i18n', 'locale', 'translation'],                   agents: ['i18n'] },
    { keywords: ['.css', '.scss', '.html', 'aria-'],                  agents: ['accessibility'] },
  ]
  for (const { keywords, agents } of pathPatterns) {
    if (filePaths.some((filePath) => keywords.some((kw) => filePath.includes(kw)))) {
      agents.forEach((agentName) => selectedNames.add(agentName))
    }
  }

  const contentPatterns: Array<{ keywords: string[]; agents: string[] }> = [
    { keywords: ['async', 'thread', 'mutex', 'semaphore'],  agents: ['concurrency', 'resource_usage'] },
    { keywords: ['route', 'endpoint', 'rest', 'graphql'],   agents: ['api_design'] },
    { keywords: ['console.log', 'console.error', 'logger'], agents: ['logging'] },
    { keywords: ['import ', 'require('],                     agents: ['dependency'] },
  ]
  for (const { keywords, agents } of contentPatterns) {
    if (keywords.some((kw) => rawDiffLower.includes(kw))) {
      agents.forEach((agentName) => selectedNames.add(agentName))
    }
  }

  if (totalAdded + totalRemoved > 200) {
    selectedNames.add('risk_scoring')
    selectedNames.add('summary')
  }

  return allAgents.filter((agentDef) => selectedNames.has(agentDef.name))
}
