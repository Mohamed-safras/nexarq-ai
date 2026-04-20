import { NextRequest, NextResponse } from 'next/server'
import { runOrchestrator, buildRunResponse } from '@nexarq/agent-runtime'
import type { RunRequest } from '@nexarq/common/interfaces'

export async function POST(request: NextRequest): Promise<NextResponse> {
  let body: RunRequest

  try {
    body = await request.json() as RunRequest
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  if (!body.diff && !body.repoPath) {
    return NextResponse.json({ error: 'Either diff or repoPath is required' }, { status: 400 })
  }

  try {
    const runResult = await runOrchestrator({
      task: 'Review the provided diff',
      ...(body.diff ? {
        diffResult: {
          rawDiff: body.diff,
          files: [],
          totalAdded: body.diff.split('\n').filter((line) => line.startsWith('+')).length,
          totalRemoved: body.diff.split('\n').filter((line) => line.startsWith('-')).length,
          changeType: 'general',
          repoType: 'unknown',
          primaryLanguage: 'unknown',
        },
      } : {}),
      triggerSource: 'sdk',
      runConfig: body.config ?? {},
    })

    return NextResponse.json(buildRunResponse(runResult))
  } catch (runError) {
    const errorMessage = runError instanceof Error ? runError.message : String(runError)
    return NextResponse.json({ error: errorMessage }, { status: 500 })
  }
}
