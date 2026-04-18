# @nexarq/sdk

TypeScript SDK for Nexarq — run 31 specialized AI code review agents programmatically.

## Install

```bash
npm install @nexarq/sdk
# or
bun add @nexarq/sdk
```

## Quick Start

```ts
import { NexarqClient } from '@nexarq/sdk'

const client = new NexarqClient({ provider: 'ollama' })

// Review a diff
const result = await client.review({
  diff: myGitDiff,
  agents: ['security', 'bugs', 'performance'],
  mode: 'smart',
})

console.log(result.summary)
// { critical: 1, high: 2, medium: 3, ... }

for (const finding of result.results) {
  console.log(`[${finding.severity}] ${finding.agentName}: ${finding.output}`)
}
```

## Streaming

```ts
for await (const event of client.streamReview({ diff: myDiff })) {
  if (event.type === 'agent:complete') {
    console.log(`${event.result.agentName} done`)
  }
  if (event.type === 'run:complete') {
    console.log('All done in', event.durationMs, 'ms')
  }
}
```

## Coding Agent

```ts
const result = await client.code({
  task: 'Add input validation to the createUser endpoint in src/routes/users.ts',
  workingDirectory: '/path/to/project',
})

console.log(result.finalOutput)
```

## Providers

| Provider | Key env var | Default model |
|---|---|---|
| `ollama` | — (local) | `codellama` |
| `openai` | `NEXARQ_OPENAI_API_KEY` | `gpt-4o` |
| `anthropic` | `NEXARQ_ANTHROPIC_API_KEY` | `claude-sonnet-4-6` |
| `google` | `NEXARQ_GOOGLE_API_KEY` | `gemini-2.5-flash` |

## LangSmith Tracing

Set these env vars to trace all agent runs in LangSmith:

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=nexarq
```
