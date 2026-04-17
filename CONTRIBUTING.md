# Contributing to Nexarq

Thanks for helping make Nexarq better. This guide covers everything you need to get a change merged.

## Ways to contribute

- **Bug reports** — open a GitHub issue with steps to reproduce and your `nexarq doctor` output
- **Feature requests** — open an issue describing the use case before writing code
- **New agents** — the highest-value contribution; see [Adding an agent](#adding-an-agent)
- **Provider support** — new LLM adapters in `packages/agent-runtime/src/providers/`
- **CLI improvements** — new commands or flags in `cli/`
- **Docs** — keep `docs/` and `AGENTS.md` in sync with code changes

## Setup

```bash
# Prerequisites: Bun 1.1+, Node 18+, Git 2.28+
git clone https://github.com/nexarq/nexarq.git
cd nexarq
bun install
cp .env.example .env
# Add at least one LLM provider key to .env
```

See [docs/development.md](docs/development.md) for the full dev guide.

## Workflow

1. Fork the repo and create a branch from `main`: `git checkout -b feat/my-change`
2. Make your changes following the conventions below
3. Run the checks: `bun test && bun run typecheck && bun run lint`
4. Open a pull request — fill in the PR template

PRs should be focused. One concern per PR. Fixes and features in separate PRs.

## Conventions

All rules are in [CLAUDE.md](CLAUDE.md). Short version:

- Agent logic lives in `agents/` — never inline prompts in CLI, SDK, or web code
- All agent execution goes through `runOrchestrator()` in `packages/agent-runtime/`
- Use `ErrorOr<T>` (`ok()` / `err()`) for every fallible operation
- Prefer streaming over batch for all LLM calls
- Never log API keys or user code — redact before any cloud call
- File names: kebab-case; PascalCase only for React components

## Adding an agent

1. Create `agents/<domain>/<name>-agent.ts` — follow the pattern in any existing agent file
2. Export it from `agents/index.ts`
3. Document it in `AGENTS.md` and `docs/agents-and-tools.md`
4. Add language/diff heuristics in `packages/agent-runtime/src/selector.ts` if it's tier 2
5. Include at least two example findings in the PR description

Domains: `security/`, `quality/`, `design/`, `docs/`, `testing/`, `meta/`
Tiers: **1** (always runs), **2** (context-selected), **meta** (post-run synthesis)

## Adding an LLM provider

1. Implement `ILLMProvider` from `@nexarq/common/interfaces` in `packages/agent-runtime/src/providers/<name>-provider.ts`
2. Reference `anthropic-provider.ts` as the canonical implementation
3. Register it in `packages/agent-runtime/src/providers/provider-factory.ts`
4. Add the provider name to `common/src/constants/provider-constants.ts`
5. Document required env vars in `docs/environment-variables.md`

## Commit messages

Use the conventional commits format:

```
feat: add SQL injection agent
fix: redact bearer tokens before Anthropic calls
docs: update agent tier table in AGENTS.md
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Security issues

Do **not** open a public issue for security vulnerabilities. See [SECURITY.md](SECURITY.md).

## License

By contributing, you agree your code is released under the [MIT License](LICENSE).
