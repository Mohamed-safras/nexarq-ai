# Nexarq — Project Knowledge

## What This Is

multi-agent code review platform + parallel coding assistant. Free and open-source, funded by ads. Three surfaces share one execution engine: CLI (`nexarq`), SDK (`@nexarq/sdk`), and web dashboard.

## Package Map

```
common/                  — Zero-dep shared types, interfaces, utils, constants. Everything imports from here.
agents/                  — 31 agent definitions (pure data + prompts). No logic, no imports outside common/.
packages/agent-runtime/  — Core execution engine. All surfaces call runOrchestrator() from here.
packages/billing/        — Ad revenue and credit tracking.
cli/                     — Commander.js CLI, git hooks, config, auth (keytar + GitHub Device Flow).
sdk/                     — NexarqClient class. Thin wrapper over agent-runtime.
web/                     — Next.js 15 dashboard + API routes. PostgreSQL + Drizzle ORM.
github-action/           — GitHub Actions integration.
```

## Dependency Rules (enforced via TypeScript project references)

- `common/` → nothing
- `agents/` → `common/` only
- `agent-runtime/` → `common/`, `agents/`
- `cli/`, `sdk/`, `web/` → `agent-runtime/`, `common/`
- Never create circular imports across packages

## Tech Stack

- **Runtime**: Bun 1.1+ (no compile step — `bun run src/index.ts` directly)
- **TypeScript 5.7**: strict, `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`
- **LLM orchestration**: LangChain + LangGraph (StateGraph for parallel agent fan-out)
- **Providers**: Anthropic (Claude), OpenAI, Google (Gemini), Ollama, MiniMax
- **CLI**: Commander.js 12, Chalk 5, Ora 8, @inquirer/prompts 8, Conf 13
- **Web**: Next.js 15 + React 19, Drizzle ORM, PostgreSQL, next-auth 5
- **Tool schemas**: Zod 3

## Architecture: Two Graph Flows, One Unified State

### Review flow (`nexarq run` / git hooks / SDK `.review()`)

```
extractDiff → selectAgents → buildNexarqGraph → [review_agent_1..N in parallel] → summary → END
```

- Each agent is a ReAct loop with read-only tools (getReadTools)
- Agent selection by trigger: pre-push = tier 1 only, scheduled = all, post-commit = diff-derived
- Results aggregated by summary-node, sorted by severity

### Coding flow (`nexarq code` / SDK `.code()`)

```
runPlannerAgent (pre-graph) → buildCodingGraph → architect → [coder_1..N in parallel] → tester → reviewer → END
```

- Planner runs before graph is built — subtask count must be known at graph-compile time
- Architect: read tools only. Coders + Tester: read + write tools
- Entry point: `runWorkflowOrchestrator(options)`

### Unified State: `NexarqGraphState`

One type for both flows in `graph/state.ts`. Review fields: `diffResult`, `agentResults`, `hasHighSeverityFinding`. Coding fields: `subtasks`, `planSummary`, `architectOutput`, `coderResults`, `testerOutput`, `reviewerOutput`. Nodes only touch fields relevant to their path.

## Tools

- **getReadTools(wd)**: read_file, search_code, list_directory, find_references, git_log, git_diff, git_status — ALL agents
- **getWriteTools(wd)**: write_file, run_command (allowlist prefix only) — coding agents only (coder + tester nodes)
- Path traversal blocked on all tools (safeResolve). File read limit: 8,000 chars. Write limit: 500KB.
- Allowed run_command prefixes: `bun test`, `jest`, `vitest`, `pytest`, `go test`, `cargo test`, `eslint`, `tsc`, `ruff`, `bun run build`. No arbitrary shell.

## Naming Conventions

- Files: kebab-case. Functions: camelCase. Types/Interfaces: PascalCase. Constants: UPPER_CASE.
- Agent names: snake_case in registry (`error_handling`, `test_coverage`), kebab in file names.
- Imports: named, with `.ts` extension (`from './foo.ts'`), package aliases (`@nexarq/common/interfaces`).

## Error Handling Pattern

```ts
type ErrorOr<T> = { ok: true; value: T } | { ok: false; error: string }
ok(value) // wrap success
err(message) // wrap failure
```

- One agent failing never stops the run — errors are isolated per node
- Only `run:error` on fatal orchestrator-level failure

## Events (All LLM calls stream)

Events fired via `onEvent(event: RunEvent)`:

- `agent:start` / `agent:chunk` / `agent:complete` / `agent:error`
- `run:plan` — list of all agent names for this run (after planning phase)
- `run:complete` — entire run finished

## Severity Levels

`critical (5) > high (4) > medium (3) > low (2) > info (1)`

- Tier 1: always run (security, secrets, bugs)
- Tier 2: context-selected from diff content
- Tier Meta: post-run synthesis agents

## What NOT To Do

- **Never inline agent prompts in CLI or web** — all prompts live in `agents/` only
- **Never call providers directly** — always go through `runOrchestrator()` or `runWorkflowOrchestrator()`
- **Never log API keys or raw user code** — redact before any cloud LLM call
- **Never allow arbitrary shell** — run_command enforces prefix allowlist, never bypass it
- **Never batch LLM calls** — always stream; use `onEvent` for real-time output
- **Never force-push main** unless explicitly asked

## Adding a New Agent

1. Create `agents/<category>/<name>-agent.ts` exporting `AgentDefinition`
2. Export from `agents/index.ts`
3. Register in `packages/agent-runtime/src/registry.ts` → `allAgents[]`
4. Add selection heuristics to `selector.ts` if language/pattern-specific
5. Document in `docs/agents-and-tools.md`

## Key Entry Points

- `packages/agent-runtime/src/orchestrator.ts` — review flow entry (`runOrchestrator`)
- `packages/agent-runtime/src/workflow-orchestrator.ts` — coding flow entry (`runWorkflowOrchestrator`)
- `packages/agent-runtime/src/selector.ts` — agent selection + `TriggerSource` union
- `packages/agent-runtime/src/graph/state.ts` — `NexarqGraphState`, `WorkflowSubtask`, `WorkflowCoderResult`, `buildStateChannels`
- `packages/agent-runtime/src/graph/graph.ts` — `buildNexarqGraph` (review) + `buildCodingGraph` (coding)
- `packages/agent-runtime/src/tools/read-tools.ts` — read-only tools for all agents
- `packages/agent-runtime/src/tools/write-tools.ts` — write + exec tools for coding agents
- `packages/agent-runtime/src/registry.ts` — `getAgent`, `getAllAgents`, `getAgentsByTier`
- `cli/src/index.ts` — CLI entry: first-run init → interactive REPL session
