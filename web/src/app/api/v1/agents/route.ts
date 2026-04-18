import { NextResponse } from 'next/server'
import { getAllAgents } from '@nexarq/agent-runtime'

export async function GET(): Promise<NextResponse> {
  const agents = getAllAgents().map((agentDef) => ({
    name:        agentDef.name,
    displayName: agentDef.displayName,
    description: agentDef.description,
    severity:    agentDef.severity,
    tier:        agentDef.tier,
    needsTools:  agentDef.needsTools,
  }))

  return NextResponse.json({ agents, total: agents.length })
}
