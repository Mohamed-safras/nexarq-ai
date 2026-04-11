# Nexarq

Nexarq is a **security-first, multi-agent code review platform** — free and open-source, funded by ads. It runs specialized AI agents across every git commit, PR, or on-demand.

## Goal

Make the best free agentic code reviewer that developers actually want to use.

## Key Technologies

- TypeScript monorepo (Bun workspaces)
- Bun runtime + package manager
- Next.js 15 (web app + API routes)
- Vercel AI SDK (multi-provider LLM routing)
- Multiple LLM providers (Anthropic / OpenAI / Google / Ollama)
- Commander.js (CLI)
- PostgreSQL + Drizzle ORM (web database)

## Repo Map

- `cli/` — TypeScript CLI, published as `nexarq` on npm
- `sdk/` — `@nexarq/sdk` TypeScript client for programmatic access
- `web/` — Next.js 15 web app + API server
- `packages/agent-runtime/` — core agent execution engine (shared by all surfaces)
- `common/` — shared types, constants, tool schemas
- `agents/` — all 31 agent definitions (TypeScript)
- `packages/billing/` — ad revenue and credit tracking
- `docs/` — global architecture docs

## Conventions

- Never force-push `main` unless explicitly requested.
- All agents live in `agents/` — never inline agent prompts in CLI or web code.
- Agent logic is centralized in `packages/agent-runtime/` — CLI, SDK, and web all import from there.
- Use `ErrorOr<T>` pattern for all fallible operations (see `common/src/types/error.ts`).
- Prefer streaming responses over batch for all LLM calls.
- Security: never log API keys, never skip redaction before cloud LLM calls.

## Docs

IMPORTANT: Read the relevant docs before implementing changes.

- `docs/architecture.md` — package dependency graph, per-package details
- `docs/request-flow.md` — full lifecycle from CLI through agent-runtime and back
- `docs/agents-and-tools.md` — agent system, tool definitions, tiering
- `docs/development.md` — dev setup, Bun workspaces, DB migrations
- `docs/environment-variables.md` — env var rules, loading order
