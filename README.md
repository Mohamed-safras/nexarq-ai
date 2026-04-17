# Nexarq

**multi-agent code review platform — free and open-source.**

Nexarq runs specialized AI agents across every git commit, PR, or on-demand task. It lives in your terminal, your CI pipeline, and your web dashboard — powered by Anthropic, OpenAI, Google, MiniMax, or local Ollama.

## Installation

**npm (recommended)**

```bash
npm install -g nexarq
```

**macOS / Linux**

```bash
curl -fsSL https://raw.githubusercontent.com/nexarq/nexarq-ai/main/install.sh | bash
```

**Windows (PowerShell)**

```powershell
irm https://raw.githubusercontent.com/nexarq/nexarq-ai/main/install.ps1 | iex
```

## Quick Start

```bash
# First run — interactive setup wizard
nexarq

# Review your last commit
nexarq run

# Run specific agents
nexarq run --agents security,bugs,performance

# Autonomous coding agent
nexarq code "refactor the auth module to use async/await"

# Generate a commit message
nexarq commit

# Fix findings from the last review
nexarq fix

# Watch mode — review as you save
nexarq watch

# Chat with your codebase
nexarq chat

# Explain recent changes in plain English
nexarq explain

# Check health of your setup
nexarq doctor
```

## Commands

| Command          | Description                                             |
| ---------------- | ------------------------------------------------------- |
| `nexarq run`     | Run review agents on your current diff                  |
| `nexarq code`    | Autonomous coding agent — reads, plans, and writes code |
| `nexarq commit`  | Generate a conventional commit message from staged diff |
| `nexarq fix`     | Auto-apply fixes for findings from the last review      |
| `nexarq watch`   | Continuously review as files change                     |
| `nexarq explain` | Plain-English walkthrough of recent changes             |
| `nexarq chat`    | Interactive chat with context about your codebase       |
| `nexarq ignore`  | Mark a finding as ignored in `.nexarqignore`            |
| `nexarq init`    | Re-run the setup wizard                                 |
| `nexarq login`   | Authenticate and store API keys in your system keyring  |
| `nexarq hook`    | Install / remove git hooks                              |
| `nexarq config`  | View and update configuration                           |
| `nexarq doctor`  | Diagnose installation and provider connectivity         |

## Agents

31 agents organized into six categories:

**Security**

| Agent           | Focus                               |
| --------------- | ----------------------------------- |
| `security`      | OWASP Top 10, injection, auth flaws |
| `secrets`       | Hardcoded keys, tokens, credentials |
| `compliance`    | GDPR, HIPAA, PCI-DSS                |
| `memory-safety` | Resource leaks, use-after-free      |

**Quality**

| Agent             | Focus                                    |
| ----------------- | ---------------------------------------- |
| `bugs`            | Logic errors, edge cases, null deref     |
| `performance`     | Complexity, N+1 queries, memory churn    |
| `concurrency`     | Race conditions, deadlocks, async issues |
| `type-safety`     | Type annotations, unsafe casts           |
| `review`          | Style, naming, best practices            |
| `refactor`        | DRY violations, complexity reduction     |
| `code-smells`     | Anti-patterns, dead code                 |
| `maintainability` | Cyclomatic complexity, readability       |
| `style`           | Formatting, linting, conventions         |
| `resource-usage`  | CPU, memory, I/O inefficiencies          |

**Design**

| Agent            | Focus                                   |
| ---------------- | --------------------------------------- |
| `architecture`   | SOLID, design patterns, coupling        |
| `api-design`     | REST conventions, versioning, contracts |
| `database`       | Query safety, migrations, indexing      |
| `dependency`     | Vulnerable or outdated packages         |
| `devops`         | Docker, CI/CD, IaC, secrets in config   |
| `error-handling` | Exception patterns, failure modes       |

**Documentation**

| Agent           | Focus                                    |
| --------------- | ---------------------------------------- |
| `docstring`     | Missing or stale documentation           |
| `logging`       | PII in logs, missing context, log levels |
| `standards`     | Project-specific coding rules            |
| `accessibility` | WCAG 2.1, ARIA, keyboard navigation      |
| `i18n`          | Hardcoded strings, locale gaps           |

**Testing**

| Agent           | Focus                            |
| --------------- | -------------------------------- |
| `test-coverage` | Missing tests, untested branches |

**Meta**

| Agent          | Focus                                   |
| -------------- | --------------------------------------- |
| `ai-fixes`     | Generates ready-to-apply code fixes     |
| `risk-scoring` | Assigns a risk score to the diff        |
| `explain`      | Plain-English summary for non-engineers |
| `summary`      | Executive overview of all findings      |
| `next-steps`   | Prioritized action list                 |

## LLM Providers

```bash
# Local — no data leaves your machine (default)
nexarq config set-provider ollama --model codellama

# Anthropic
nexarq login --provider anthropic
nexarq config set-provider anthropic --model claude-sonnet-4-6

# OpenAI
nexarq login --provider openai
nexarq config set-provider openai --model gpt-4o

# Google
nexarq login --provider google
nexarq config set-provider google --model gemini-2.5-flash

# MiniMax
nexarq login --provider minimax
nexarq config set-provider minimax
```

Cloud providers require explicit consent (`cloud_consent: true`) and are disabled by default.

## GitHub Action

Add Nexarq to any workflow:

```yaml
- uses: nexarq/nexarq-ai@main
  with:
    provider: google
    google-api-key: ${{ secrets.GOOGLE_API_KEY }}
    mode: smart # fast | smart | deep
    fail-on: high # critical | high | medium | none
    post-comment: true # posts findings as a PR review comment
```

**Inputs**: `provider`, `anthropic-api-key`, `openai-api-key`, `google-api-key`, `minimax-api-key`, `model`, `mode`, `agents`, `fail-on`, `post-comment`, `github-token`

**Outputs**: `findings-count`, `critical-count`, `high-count`, `summary`

## SDK

```typescript
import { NexarqClient } from '@nexarq/sdk'

const client = new NexarqClient({ provider: 'anthropic' })

// Review a diff
const result = await client.review({ diff, agents: ['security', 'bugs'] })

// Autonomous coding task
const result = await client.code({
  task: 'add input validation to the login handler',
})
```

## Security Model

- API keys stored in system keyring — never plain text or env files
- Diffs are redacted before any cloud send (secrets, tokens auto-removed)
- Cloud providers disabled by default (`cloud_consent: false`)
- Agents operate on diffs only — never the full repository
- Prompt injection detection on all LLM outputs
- Full audit log at `~/.nexarq/logs/`

## Git Hooks

```bash
nexarq hook install post-commit   # auto-review after every commit
nexarq hook install pre-push      # review before push
nexarq hook status
nexarq hook remove post-commit
```

## Configuration

```bash
nexarq config show
nexarq config set-agents security,bugs,review
nexarq config set-provider anthropic --model claude-sonnet-4-6
nexarq config add-standards ./CODING_STANDARDS.md
```

Config location: `~/.nexarq/config.yaml`

## Repo Structure

```
agents/          — 31 agent definitions (security, quality, design, docs, testing, meta)
cli/             — nexarq CLI (Commander.js, published to npm)
sdk/             — @nexarq/sdk TypeScript client
web/             — Next.js 15 web app + API server
packages/
  agent-runtime/ — core execution engine (shared by CLI, SDK, web)
  billing/       — ad revenue and credit tracking
common/          — shared types, constants, interfaces
github-action/   — nexarq/nexarq-ai GitHub Action
docs/            — architecture and development guides
```

## Contributing

Nexarq is free and open-source. Contributions are welcome — new agents, LLM provider adapters, CLI improvements, and bug fixes.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before participating.

## Security

To report a vulnerability privately, see [SECURITY.md](SECURITY.md). Do not open a public issue.

## License

MIT — see [LICENSE](LICENSE).
