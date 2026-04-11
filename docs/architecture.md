# Architecture

## Package Graph

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Surfaces                            │
│                                                                 │
│  cli/          sdk/            web/           git hooks         │
│  (npm: nexarq) (@nexarq/sdk)   (Next.js 15)   (post-commit,     │
│                                               pre-push, etc.)  │
└──────────┬──────────┬──────────┬──────────────────┬────────────┘
           │          │          │                  │
           └──────────┴──────────┴──────────────────┘
                                │
                                ▼
                  ┌─────────────────────────┐
                  │  packages/agent-runtime │
                  │                         │
                  │  orchestrator.ts        │  ← single entry point
                  │  graph/ (LangGraph)     │  ← StateGraph
                  │  providers/             │  ← LLM adapters
                  │  selector.ts            │  ← agent routing
                  │  tools/                 │  ← review + coding tools
                  │  tracing/               │  ← LangSmith
                  │  registry.ts            │  ← agent lookup
                  └────────────┬────────────┘
                               │  imports
                  ┌────────────┴────────────┐
                  │  agents │
                  │  agents/index.ts         │
                  └────────────┬────────────┘
                               │  imports
                  ┌────────────┴────────────┐
                  │  common/                │
                  │  types/, interfaces/    │
                  │  constants/, utils/     │
                  └─────────────────────────┘
```

## Packages

### `common/` — `@nexarq/common`

Shared TypeScript types, interfaces, constants, and utility functions. Zero runtime dependencies — everything here is pure types or tiny pure functions. All other packages import from here.

Key exports:

- `@nexarq/common/types` — `Severity`, `AgentMode`, `AgentTier`, `ProviderName`, `RunEvent`, `ErrorOr<T>`
- `@nexarq/common/interfaces` — `AgentDefinition`, `AgentResult`, `RunConfig`, `FileDiff`, `ILLMProvider`
- `@nexarq/common/constants` — agent constants, provider defaults, security patterns
- `@nexarq/common/utils` — `ok()`, `err()`, `compareSeverity()`, `maxSeverity()`

### `agents/`

All 31 agent definitions as flat TypeScript files. Each exports a single `AgentDefinition` constant. No business logic — only the `systemPrompt` string and a `buildPrompt()` function. Agents are organized into tiers:

| Tier | When               | Agents                                                                                                                                                                                                                                                        |
| ---- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | Always run         | security, secrets, bugs, performance, review                                                                                                                                                                                                                  |
| 2    | Context-selected   | architecture, api-design, database, error-handling, concurrency, memory-safety, resource-usage, type-safety, code-smells, style, refactor, maintainability, dependency, devops, docstring, test-coverage, logging, compliance, accessibility, i18n, standards |
| Meta | Post-run synthesis | ai-fixes, risk-scoring, explain, summary, next-steps                                                                                                                                                                                                          |

### `packages/agent-runtime/` — `@nexarq/agent-runtime`

The execution engine. Shared by CLI, SDK, web API, and git hooks. Never imported by `common/` or `agents/`.

Key modules:

- **`orchestrator.ts`** — `runOrchestrator(config)` — the single entry point for all surfaces
- **`graph/graph.ts`** — `buildNexarqGraph()` — single LangGraph `StateGraph` with two paths: review fan-out and coding-agent ReAct loop
- **`graph/state.ts`** — `NexarqGraphState` — unified state for both paths
- **`selector.ts`** — `selectAgents(triggerSource, diff, config)` — tier-based routing with trigger-source overrides
- **`providers/`** — Anthropic, OpenAI, Google, Ollama adapters via LangChain
- **`tools/review-tools.ts`** — read-only tools: `read_file`, `search_code`, `list_directory`, `find_references`, `git_log`
- **`tools/coding-tools.ts`** — read-write tools: `write_file`, `run_command`, `git_diff`, `git_status`
- **`tracing/langsmith-tracer.ts`** — wraps runs with LangSmith tracing when env vars are set
- **`registry.ts`** — `getAgent(name)`, `getAllAgents()`, `getAgentsByTier()`

### `cli/` — npm package `nexarq`

Commander.js CLI. Calls `runOrchestrator()` from agent-runtime. Manages config (Conf), API keys (keytar), git hooks, and auth (GitHub Device Flow).

Commands: `run`, `code`, `init`, `hook`, `config`, `login`, `doctor`

### `sdk/` — npm package `@nexarq/sdk`

Thin TypeScript client wrapper. Exposes `NexarqClient` with `review()`, `code()`, and `streamReview()` (async generator). Internally calls `runOrchestrator()`.

### `web/` — Next.js 15 app

Landing page, dashboard, and API server. Uses next-auth for sessions, Drizzle ORM + PostgreSQL for persistence.

Key routes:

- `POST /api/v1/run` — run agents via HTTP
- `GET /api/v1/agents` — list all agent definitions
- `POST /api/webhooks/github` — GitHub PR webhook (HMAC verified)
- `GET /api/healthz` — health check

## Dependency Rules

- `common/` must not import from any other monorepo package
- `agents/` imports only from `@nexarq/common`
- `packages/agent-runtime/` imports from `@nexarq/common` and `agents/`
- `cli/`, `sdk/`, `web/` import from `@nexarq/agent-runtime` and `@nexarq/common`
- No circular imports — enforced by TypeScript project references

## Runtime

All packages use **Bun** as the runtime and package manager. TypeScript source is run directly (`bun run src/index.ts`) — no compilation step in development. Production builds use `bun build` to bundle for distribution.
