import type { AgentDefinition } from '@nexarq/common/interfaces'
import {
  securityAgent, secretsAgent, bugsAgent,
  performanceAgent, reviewAgent, architectureAgent,
  apiDesignAgent, databaseAgent, errorHandlingAgent,
  concurrencyAgent, memorySafetyAgent, resourceUsageAgent,
  typeSafetyAgent, codeSmellsAgent, styleAgent,
  refactorAgent, maintainabilityAgent, dependencyAgent,
  devopsAgent, docstringAgent, testCoverageAgent,
  loggingAgent, complianceAgent, accessibilityAgent,
  i18nAgent, standardsAgent, aiFixesAgent,
  riskScoringAgent, explainAgent, summaryAgent, nextStepsAgent,
} from '../../../agents/index.ts'

const allAgents: AgentDefinition[] = [
  // Tier 1 — always run
  securityAgent,
  secretsAgent,
  bugsAgent,

  // Tier 2 — quality
  performanceAgent,
  reviewAgent,
  architectureAgent,
  apiDesignAgent,
  databaseAgent,
  errorHandlingAgent,
  concurrencyAgent,
  memorySafetyAgent,
  resourceUsageAgent,
  typeSafetyAgent,
  codeSmellsAgent,
  styleAgent,
  refactorAgent,
  maintainabilityAgent,
  dependencyAgent,
  devopsAgent,

  // Tier 2 — docs and testing
  docstringAgent,
  testCoverageAgent,
  loggingAgent,

  // Tier 2 — compliance and accessibility
  complianceAgent,
  accessibilityAgent,
  i18nAgent,
  standardsAgent,

  // Meta-agents
  aiFixesAgent,
  riskScoringAgent,
  explainAgent,
  summaryAgent,
  nextStepsAgent,
]

const agentMap = new Map<string, AgentDefinition>(
  allAgents.map((agentDef) => [agentDef.name, agentDef])
)

export function getAgent(agentName: string): AgentDefinition | undefined {
  return agentMap.get(agentName)
}

export function getAllAgents(): AgentDefinition[] {
  return allAgents
}

export function getAgentsByTier(tier: 1 | 2 | 3): AgentDefinition[] {
  return allAgents.filter((agentDef) => agentDef.tier === tier)
}

export function getAgentNames(): string[] {
  return allAgents.map((agentDef) => agentDef.name)
}
