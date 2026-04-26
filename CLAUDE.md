# Nexarq

Nexarq is a **multi-agent code review platform and general coding assistant** — free and open-source, funded by ads. It runs specialized AI agents across every git commit, PR, or on-demand, and acts as an interactive coding assistant when run directly.

## Goal

Make the best free agentic code reviewer and coding assistant that developers actually want to use.

## Key Technologies

- TypeScript monorepo (Bun workspaces)
- Bun runtime + package manager
- LangGraph 0.2.x (StateGraph for parallel agent fan-out and ReAct loops)
- LangChain (tool definitions, model adapters)
- Next.js 15 (web app + API routes)
- Multiple LLM providers: Anthropic / OpenAI / Google / Ollama
- Commander.js (CLI) + readline (interactive REPL)
- PostgreSQL + Drizzle ORM (web database)
- Playwright (browser automation, optional)
- Brave Search + Jina Reader (web search + docs, optional)

## Repo Map

- `cli/` — TypeScript CLI, published as `nexarq` on npm
- `sdk/` — `@nexarq/sdk` TypeScript client for programmatic access
- `web/` — Next.js 15 web app + API server
- `packages/agent-runtime/` — core agent execution engine (shared by all surfaces)
- `common/` — shared types, constants, tool schemas
- `agents/` — all 31 agent definitions (TypeScript)
- `packages/billing/` — ad revenue and credit tracking
- `docs/` — global architecture docs

## Three Entry Points (agent-runtime)

| Function                    | File                           | Use case                                                      |
| --------------------------- | ------------------------------ | ------------------------------------------------------------- |
| `runOrchestrator()`         | `orchestrator.ts`              | Parallel review fan-out (git hooks, `nexarq run`)             |
| `runWorkflowOrchestrator()` | `workflow-orchestrator.ts`     | Multi-agent coding team (`nexarq code`)                       |
| `runConversationTurn()`     | `conversation-orchestrator.ts` | Persistent chat with all tools (`nexarq` REPL, `nexarq chat`) |

## Conventions

- Never force-push `main` unless explicitly requested.
- All agents live in `agents/` — never inline agent prompts in CLI or web code.
- Agent logic is centralized in `packages/agent-runtime/` — CLI, SDK, and web all import from there.
- Use `ErrorOr<T>` pattern for all fallible operations (see `common/src/types/error.ts`).
- Prefer streaming responses over batch for all LLM calls.
- Security: never log API keys, never skip redaction before cloud LLM calls.
- Tool sets are composed per surface — see `docs/agents-and-tools.md` for the composition table.
- `unsafeShell` must never be enabled by default — always opt-in via config or `RunConfig`.

## Docs

IMPORTANT: Read the relevant docs before implementing changes.

- `docs/architecture.md` — package dependency graph, per-package details, CLI command table
- `docs/agents-and-tools.md` — agent system, all tool sets, composition per surface
- `docs/request-flow.md` — full lifecycle from CLI through agent-runtime and back
- `docs/environment-variables.md` — env var rules, loading order, new keys (Brave, Jina)
- `docs/development.md` — dev setup, Bun workspaces, DB migrations
- `docs/feature-guide.md` — step-by-step testing guide for every feature
