---
name: nexarq
description: Nexarq dev command center -- add agents, create CLI commands, run reviews, explore architecture, manage providers
user_invocable: true
args: mode
argument-hint: "[agent | command | review | provider | migration | docs | build | (empty)]"
---

# nexarq -- Router

## Mode Routing

Determine the mode from `{{mode}}`:

| Input | Mode |
|-------|------|
| (empty / no args) | `discovery` -- Show command menu |
| `agent` | `agent` -- Scaffold a new agent |
| `command` | `command` -- Scaffold a new CLI command |
| `review` | `review` -- Run a security + quality review of current changes |
| `provider` | `provider` -- Add or debug an LLM provider |
| `migration` | `migration` -- Generate and apply a DB schema migration (web) |
| `docs` | `docs` -- Load architecture docs into context and answer questions |
| `build` | `build` -- Check build health across all packages |

---

## Discovery Mode (no arguments)

Show this menu:

```
nexarq dev -- Command Center

  /nexarq agent      → Scaffold a new agent (prompts for domain, name, tier, severity)
  /nexarq command    → Scaffold a new CLI command (Commander.js pattern)
  /nexarq review     → Security + quality review of staged/branch changes
  /nexarq provider   → Add or debug an LLM provider in packages/agent-runtime
  /nexarq migration  → Generate + apply Drizzle DB migration (web only)
  /nexarq docs       → Load architecture docs and answer questions
  /nexarq build      → Run build health check across all workspace packages
```

---

## Context Loading by Mode

After determining the mode, read the relevant files before executing:

### `agent`
Read:
- `docs/agents-and-tools.md`
- `agents/index.ts`
- One example agent from the target domain (e.g. `agents/security/security-agent.ts`)
- `common/src/interfaces/agent/index.ts`

Then:
1. Ask: agent name, domain (security / quality / design / docs / testing / meta), tier (1/2/3), severity (critical/high/medium/low/info), and a one-line description.
2. Scaffold `agents/<domain>/<name>-agent.ts` following the existing pattern: `instructions` const, `buildPrompt()` function, named export matching `AgentDefinition`.
3. Add the export to `agents/index.ts`.
4. Remind the user to: update `docs/agents-and-tools.md`, add selector heuristics in `packages/agent-runtime/src/selector.ts` if tier 2.

### `command`
Read:
- `cli/src/index.ts`
- One example command (e.g. `cli/src/commands/run-command.ts`)
- `common/src/interfaces/run/index.ts`

Then:
1. Ask: command name, one-line description, options/flags needed.
2. Scaffold `cli/src/commands/<name>-command.ts` following the existing pattern (Commander.js action, lazy import, spinner, ErrorOr<T> returns).
3. Register it in `cli/src/index.ts`.

### `review`
Use the `security-review` skill on the current branch changes. Additionally:
- Check that no agent prompts are inlined in `cli/` or `web/` (must live in `agents/`).
- Verify no API keys appear in staged files.
- Check all fallible functions use `ErrorOr<T>`.

### `provider`
Read:
- `packages/agent-runtime/src/providers/anthropic-provider.ts` (reference implementation)
- `common/src/interfaces/llm/llm-provider.ts`
- `common/src/constants/provider-constants.ts`

Then:
1. If adding: scaffold `packages/agent-runtime/src/providers/<name>-provider.ts` implementing `LLMProvider`.
2. If debugging: diff the provider against the reference implementation and identify divergence.
3. Remind the user to register the new provider in `provider-factory.ts`.

### `migration`
Read:
- `docs/development.md` (migration section)
- `web/src/db/schema/` (relevant schema files)

Then:
1. Show the current schema changes.
2. Run: `bun run --cwd web db:generate` to generate migration SQL.
3. Review the generated migration for safety (no destructive drops on populated tables without confirmation).
4. On confirmation: `bun run --cwd web db:migrate`.

### `docs`
Read all of:
- `docs/architecture.md`
- `docs/request-flow.md`
- `docs/agents-and-tools.md`
- `docs/development.md`
- `docs/environment-variables.md`

Then answer the user's question with specific file and line references.

### `build`
Run in sequence:
```
bun run build --filter='./common'
bun run build --filter='./packages/agent-runtime'
bun run build --filter='./cli'
bun run build --filter='./sdk'
```
Report any errors with file:line references. Do not proceed past a package that fails.
