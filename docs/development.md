# Development Guide

## Prerequisites

- [Bun](https://bun.sh) 1.1+ — runtime and package manager (`curl -fsSL https://bun.sh/install | bash`)
- Node.js 18+ — needed for some tooling (Next.js build, etc.)
- Git 2.28+
- PostgreSQL 15+ (for web/ database; optional for CLI-only development)

## Setup

```bash
# Clone the repo
git clone https://github.com/nexarq/nexarq.git
cd nexarq

# Install all workspace dependencies
bun install

# Copy env vars
cp .env.example .env
# Edit .env and set at minimum one LLM provider key:
#   NEXARQ_ANTHROPIC_API_KEY, NEXARQ_OPENAI_API_KEY, or NEXARQ_GOOGLE_API_KEY
#   (or leave blank if using Ollama locally)
```

## Running Packages

```bash
# CLI — run directly from source
bun run cli/src/index.ts run --diff "$(git diff HEAD~1 HEAD)"

# Or via the local bin (after bun install links it)
./cli/bin/nexarq.js run

# Web app
bun run --cwd web dev

# Run a specific agent in isolation
bun run -e "
  import { getAgent } from './packages/agent-runtime/src/registry.ts'
  const agent = getAgent('security')
  console.log(agent?.description)
"
```

## Workspace Structure

```
nexarq-ai/
├── bun.lockb
├── package.json          ← workspace root
├── tsconfig.base.json    ← base TS config for all packages
├── bunfig.toml
├── .env.example
├── CLAUDE.md             ← AI coding conventions
├── AGENTS.md             ← canonical agent registry
│
├── common/               ← @nexarq/common  (zero deps)
├── agents/               ← agent definitions (imports common only)
├── packages/
│   └── agent-runtime/    ← @nexarq/agent-runtime  (LangChain/LangGraph)
├── cli/                  ← npm: nexarq
├── sdk/                  ← npm: @nexarq/sdk
├── web/                  ← Next.js 15 app
└── docs/                 ← this directory
```

## Bun Workspaces

All packages are registered in the root `package.json`:

```json
{
  "workspaces": ["common", "packages/*", "cli", "sdk", "web"]
}
```

After `bun install`, each package's `node_modules` symlinks are hoisted to the root. Cross-package imports (`@nexarq/common`, `@nexarq/agent-runtime`) resolve automatically.

TypeScript path aliases in `tsconfig.base.json` mirror the workspace packages so IDE tooling resolves imports without a compilation step.

## TypeScript

- **Runtime**: Bun executes `.ts` files directly — no `tsc` emit in development
- **`allowImportingTsExtensions: true`** — import files with `.ts` extension
- **`noEmit: true`** — required when using `allowImportingTsExtensions`
- **`lib: ["ES2022", "DOM"]`** — provides `fetch`, `URL`, `Response`, etc.

Type-check without emitting:
```bash
bun run tsc --noEmit -p tsconfig.base.json
```

## Adding a New Agent

1. Create `agents/my-agent-agent.ts` following the pattern of any existing agent:
   ```ts
   import type { AgentDefinition } from '@nexarq/common/interfaces'
   import { buildUserPrompt, SHARED_SYSTEM_PREFIX } from './agent-template'

   const instructions = `Focus ONLY on X in this diff. Check for: ...`

   export const myAgentAgent: AgentDefinition = {
     name: 'my-agent',
     displayName: 'My Agent',
     description: 'Short description shown in --list-agents',
     severity: 'medium',
     tier: 2,
     needsTools: false,
     systemPrompt: SHARED_SYSTEM_PREFIX,
     buildPrompt: (diff, language, context) =>
       buildUserPrompt(instructions, diff, language, context),
   }
   ```
2. Export it from `agents/index.ts`
3. Document it in `AGENTS.md` and `docs/agents-and-tools.md`
4. Add language heuristics in `packages/agent-runtime/src/selector.ts` if applicable

## Database (web/)

The web app uses Drizzle ORM with PostgreSQL.

```bash
# Set DATABASE_URL in .env
# Run migrations
bun run --cwd web db:migrate

# Generate a new migration after schema changes
bun run --cwd web db:generate
```

Schema files are in `web/src/db/schema/`.

## Running Tests

```bash
# All packages
bun test

# Specific package
bun test --cwd packages/agent-runtime

# Watch mode
bun test --watch
```

## Building for Production

```bash
# CLI — bundle to dist/
bun build cli/src/index.ts --outdir cli/dist --target bun

# Web — Next.js build
bun run --cwd web build

# SDK — bundle for npm publish
bun build sdk/src/index.ts --outdir sdk/dist --target node
```

## Publishing

```bash
# CLI (public, name: nexarq)
cd cli && npm publish

# SDK (public, name: @nexarq/sdk)
cd sdk && npm publish --access public
```

The `web/` package is deployed to Vercel — not published to npm.

## Code Conventions

See `CLAUDE.md` in the repo root for the full list. Key rules:

- All agent logic lives in `agents/` — never inline prompts elsewhere
- All agent execution goes through `runOrchestrator()` — never call providers directly from CLI or web
- Use `ErrorOr<T>` for fallible operations (`ok()` / `err()`)
- Prefer streaming over batch for all LLM calls
- Never log API keys or user code — redact before any cloud call
- File names: kebab-case for all files; PascalCase only for React components
- Variable names: no single-letter variables except loop indices
