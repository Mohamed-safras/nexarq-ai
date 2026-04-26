# Environment Variables

## Loading Order

Variables are resolved in this priority order (highest wins):

1. **Shell environment** — `export VAR=value` or set in CI secrets
2. **Project `.env`** — `.nexarq.json` in the git repo root (CLI only)
3. **Global config** — `~/.nexarq/config.json` (CLI only)
4. **`.env` file** — loaded by Next.js (web), Bun (packages), or `dotenv` (SDK)
5. **Defaults** — hardcoded in `packages/agent-runtime/src/providers/provider-factory.ts`

## LLM Provider Keys

Exactly one provider key is required for the tool to run. If multiple are set, the active provider from config takes precedence.

| Variable | Provider | Required |
|----------|----------|----------|
| `NEXARQ_ANTHROPIC_API_KEY` | Anthropic (Claude) | One of these |
| `NEXARQ_OPENAI_API_KEY` | OpenAI (GPT-4o) | One of these |
| `NEXARQ_GOOGLE_API_KEY` | Google (Gemini) | One of these |
| `NEXARQ_OLLAMA_URL` | Ollama (local) | Optional, default: `http://localhost:11434` |
| `NEXARQ_OLLAMA_MODEL` | Ollama model name | Optional, default: `codellama` |

Keys are stored in the system keyring (keytar) by `nexarq init` — not in files. If keytar is unavailable, the env var fallback is used.

**Security:** Keys are never logged, never included in git commits, and never sent to Nexarq servers. They go directly to the LLM provider API.

## GitHub Integration

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXARQ_GITHUB_CLIENT_ID` | GitHub OAuth App client ID for Device Flow login | Web + CLI login |
| `NEXARQ_GITHUB_CLIENT_SECRET` | GitHub OAuth App client secret | Web only |
| `NEXARQ_GITHUB_WEBHOOK_SECRET` | HMAC secret for verifying webhook payloads | Web webhook |

## Web Search & Docs (optional)

Used by the `web_search` and `read_docs` tools in the conversation and coding agents.

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXARQ_BRAVE_API_KEY` | Brave Search API key — enables `web_search` and auto-docs lookup | Optional (tools degrade gracefully without it) |
| `NEXARQ_JINA_API_KEY` | Jina Reader API key — higher rate limits for doc fetching | Optional (Jina works without key at lower limits) |

Without `NEXARQ_BRAVE_API_KEY`, `web_search` and `read_docs` return a "key not configured" message. Web search is not required for code review or coding — only for research and docs-aware assistance.

## LangSmith Tracing

All optional. When `LANGCHAIN_TRACING_V2=true`, every agent run is traced.

| Variable | Description |
|----------|-------------|
| `LANGCHAIN_TRACING_V2` | Set to `true` to enable tracing |
| `LANGCHAIN_API_KEY` | Your LangSmith API key |
| `LANGCHAIN_PROJECT` | Project name in LangSmith dashboard (default: `nexarq`) |
| `LANGCHAIN_ENDPOINT` | LangSmith API endpoint (default: `https://api.smith.langchain.com`) |

## Web App

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes (web) |
| `NEXTAUTH_URL` | Full URL of the web app (e.g., `https://nexarq.dev`) | Yes (web) |
| `NEXTAUTH_SECRET` | Random secret for NextAuth session encryption | Yes (web) |

## Analytics & Ads

All optional. The app works without these — analytics and ads are simply disabled.

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_POSTHOG_KEY` | PostHog project API key for usage analytics |
| `NEXT_PUBLIC_POSTHOG_HOST` | PostHog host (default: `https://app.posthog.com`) |
| `CARBON_ADS_SERVE` | Carbon Ads serve code (e.g., `CK7DT53J`) |
| `CARBON_ADS_PLACEMENT` | Carbon Ads placement ID |

## CLI Behavior

| Variable | Description |
|----------|-------------|
| `NEXARQ_SKIP` | Set to `1` to skip review in git hooks (e.g., `NEXARQ_SKIP=1 git commit`) |
| `NEXARQ_NO_COLOR` | Set to `1` to disable colored output |
| `NEXARQ_NO_ADS` | Set to `1` to disable CLI ad banners |
| `NEXARQ_DEBUG` | Set to `1` to enable verbose debug logging |
| `NEXARQ_CONFIG_PATH` | Override path to project config file |

## Example `.env`

A complete template is at `.env.example` in the repo root. Copy it to `.env` and fill in what you need:

```bash
cp .env.example .env
```

**Do not commit `.env` to git.** It is listed in `.gitignore`.

## Secrets in CI

For GitHub Actions, set secrets in the repository settings and reference them in the workflow:

```yaml
env:
  NEXARQ_ANTHROPIC_API_KEY: ${{ secrets.NEXARQ_ANTHROPIC_API_KEY }}
  LANGCHAIN_TRACING_V2: true
  LANGCHAIN_API_KEY: ${{ secrets.LANGCHAIN_API_KEY }}
  LANGCHAIN_PROJECT: nexarq-ci
```
