# Nexarq CLI

**Security-first, hybrid multi-agent code review platform powered by LLMs.**

Nexarq is an agentic code review CLI that lives in your terminal — it reads your diffs, runs 22 specialized AI agents across security, performance, architecture, and more, and delivers prioritized findings directly in your shell or on every git commit.

## Installation

**macOS / Linux**
```bash
curl -fsSL https://raw.githubusercontent.com/nexarq/nexarq-cli/main/install.sh | bash
```

**Windows (PowerShell)**
```powershell
irm https://raw.githubusercontent.com/nexarq/nexarq-cli/main/install.ps1 | iex
```

**Via pip**
```bash
pip install nexarq-cli
```

The installer creates an isolated environment, registers the `nexarq` command globally, and wires up git hooks automatically. Open a new terminal when done.

## Quick Start

```bash
# Set up for your project (interactive wizard)
nexarq init

# Verify installation
nexarq doctor

# Review your last commit
nexarq run

# Run specific agents
nexarq run --agents security,bugs,performance

# List all 22 available agents
nexarq run --list-agents

# Full help
nexarq help
```

## Features

- **22 specialized review agents**: security, bugs, performance, architecture, devops, and more
- **Hybrid LLM support**: local Ollama + OpenAI, Anthropic, Google cloud providers
- **Security-first design**: diff-only by default, keyring storage, prompt injection defense
- **Git integration**: post-commit and pre-push hooks
- **MCP server support**: extensible via Model Context Protocol servers
- **Rich terminal output**: color-coded severity, summary tables, audit logs

## Agents

| Agent | Focus |
|-------|-------|
| `security` | OWASP Top 10, secrets, injection |
| `bugs` | Logic errors, edge cases |
| `performance` | Complexity, N+1, memory |
| `review` | Style, naming, best practices |
| `architecture` | SOLID, design patterns |
| `devops` | Docker, CI/CD, IaC |
| `refactor` | DRY, complexity reduction |
| `docstring` | Missing documentation |
| `type_safety` | Type annotations |
| `test_coverage` | Missing tests |
| `dependency` | Vulnerable packages |
| `api_design` | REST conventions |
| `database` | Query safety, migrations |
| `concurrency` | Race conditions, async |
| `error_handling` | Exception patterns |
| `logging` | PII in logs, log levels |
| `maintainability` | Cyclomatic complexity |
| `accessibility` | WCAG 2.1, ARIA |
| `compliance` | GDPR, HIPAA, PCI-DSS |
| `explain` | Plain-English walkthrough |
| `memory_safety` | Resource leaks |
| `standards` | Project-specific rules |

## LLM Providers

```bash
# Local (default – no data leaves your machine)
nexarq config set-provider ollama --model codellama

# Cloud (requires API key and explicit consent)
nexarq config set-provider openai --model gpt-4o
nexarq config set-key openai
nexarq config cloud-consent true
```

## Security Model

- API keys stored in system keyring (never plain text)
- Diffs are redacted before cloud sends (secrets, tokens auto-removed)
- Cloud providers disabled by default (`cloud_consent: false`)
- Agents operate on diffs only – never the full repository
- Prompt injection detection on all LLM outputs
- Full audit log at `~/.nexarq/logs/`

## Configuration

```bash
nexarq config show                     # View current config
nexarq config set-agents security,bugs,review
nexarq config add-standards ./CODING_STANDARDS.md
nexarq config list-profiles
```

Config location: `~/.nexarq/config.yaml`

## Git Hooks

```bash
nexarq hook install post-commit   # Auto-review after every commit
nexarq hook install pre-push      # Review before push
nexarq hook status
```

## License

MIT
