# Request Flow

This document traces a full lifecycle for each surface, from trigger to output.

## 1. CLI — `nexarq run` (post-commit hook)

```
git commit
  └─► .git/hooks/post-commit
        └─► nexarq run --hook post-commit
              │
              ├─ [diff-extractor.ts]
              │   extractDiff()
              │   • checks NEXARQ_SKIP=1  →  exit 0
              │   • git diff HEAD~1 HEAD  (or --cached for first commit)
              │
              ├─ [config-loader.ts]
              │   loadConfig()
              │   • reads .nexarq.json (project) or ~/.nexarq/config.json (global)
              │   • merges with env vars
              │
              ├─ [orchestrator.ts]
              │   runOrchestrator({ diff, triggerSource: 'post-commit', ... })
              │   │
              │   ├─ [selector.ts]
              │   │   selectAgents('post-commit', diff, config)
              │   │   • always includes Tier 1 agents
              │   │   • adds Tier 2 agents based on diff content
              │   │   • returns AgentSelectionPlan
              │   │
              │   ├─ [providers/provider-factory.ts]
              │   │   getProvider(config.provider)
              │   │   • returns cached ChatModel instance
              │   │
              │   ├─ [graph/graph.ts]
              │   │   buildNexarqGraph()
              │   │   • StateGraph: router → review_fan_out → summary
              │   │
              │   └─ graph.stream(initialState)
              │       • router node: sets path = 'review'
              │       • review nodes: run selected agents in parallel
              │         each calls ChatModel.invoke(systemPrompt + userPrompt)
              │         yields agent:start, agent:chunk, agent:complete events
              │       • summary node: assembles RunResponse
              │
              └─ [formatter.ts]
                  printSummary(results)
                  • prints findings grouped by severity
                  • prints ad banner (1-in-5 runs, non-blocking)
```

## 2. CLI — `nexarq code <task>` (coding agent)

```
nexarq code "Add input validation to createUser endpoint"
  │
  ├─ [code-command.ts]
  │   buildRunConfig({ triggerSource: 'coding-agent', task, workingDirectory })
  │
  └─ [orchestrator.ts]
      runOrchestrator({ triggerSource: 'coding-agent', task, ... })
      │
      ├─ [selector.ts]
      │   selectAgents('coding-agent', ...)
      │   • returns empty agentNames — coding agent handles itself
      │
      ├─ [graph/graph.ts]
      │   buildNexarqGraph()
      │   • router node: sets path = 'coding_agent'
      │
      └─ [graph/nodes/coding-agent-node.ts]
          createReactAgent(model, getCodingTools())
          • tools: write_file, run_command (allowlisted), git_diff, git_status
          • ReAct loop: think → tool → observe → think → ...
          • yields events as agent works
          • terminates when task complete or max iterations reached
```

## 3. SDK — `client.review({ diff })`

```
const client = new NexarqClient({ provider: 'anthropic' })
const result = await client.review({ diff, agents: ['security', 'bugs'] })
  │
  └─ [sdk/src/client.ts]
      buildRunConfig({ triggerSource: 'sdk', agents, ... })
      runOrchestrator(config)  ← same path as CLI
        └─ returns RunResponse
```

## 4. SDK — `client.streamReview({ diff })` (streaming)

```
for await (const event of client.streamReview({ diff })) { ... }
  │
  └─ [sdk/src/client.ts]
      buildRunConfig({ triggerSource: 'sdk', ... })
      runOrchestratorStream(config)  ← yields RunEvents from graph.stream()
        • 'agent:start'    — agent began running
        • 'agent:chunk'    — LLM token streamed
        • 'agent:complete' — agent finished, result attached
        • 'agent:error'    — agent failed (non-fatal, others continue)
        • 'run:complete'   — all agents done, summary attached
        • 'run:error'      — fatal orchestrator error
```

## 5. Web API — `POST /api/v1/run`

```
POST /api/v1/run
  Body: { diff, agents?, provider?, mode?, context? }
  │
  └─ [web/src/app/api/v1/run/route.ts]
      zod.parse(body)
      runOrchestrator({ triggerSource: 'sdk', ...body })
      return NextResponse.json(result)
```

## 6. GitHub Webhook — `POST /api/webhooks/github`

```
GitHub sends PR event
  │
  └─ [web/src/app/api/webhooks/github/route.ts]
      verifyHmacSignature(request, NEXARQ_GITHUB_WEBHOOK_SECRET)
      │
      ├─ filter: only 'pull_request' events with action 'opened'|'synchronize'
      │
      ├─ fetch PR diff from GitHub API
      │   GET /repos/:owner/:repo/pulls/:number
      │   Accept: application/vnd.github.v3.diff
      │
      └─ runOrchestrator({ triggerSource: 'pr-review', diff, context: prContext })
          • returns RunResponse
          • (future) post review comment back to GitHub PR
```

## LangSmith Tracing

When `LANGCHAIN_TRACING_V2=true` is set, every `runOrchestrator()` call is automatically wrapped by LangSmith via the `@traceable` decorator applied in `langsmith-tracer.ts`. Each agent run appears as a child span with:
- Provider name and model
- Agent name and tier
- Token usage
- Duration
- Full prompt and completion

No code changes needed to enable tracing — set the env vars and traces appear in the LangSmith dashboard under the `LANGCHAIN_PROJECT` project name.

## Error Handling

All fallible operations use `ErrorOr<T>` (from `@nexarq/common/types`):
- `ok(value)` — success
- `err(message, code?)` — failure with human-readable message

Agents that error are marked `agent:error` and skipped — the run continues. A run only emits `run:error` if the orchestrator itself fails (e.g., no provider configured, no diff provided).
