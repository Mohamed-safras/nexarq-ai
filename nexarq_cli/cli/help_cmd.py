"""nexarq help – extended help and guidance."""
from __future__ import annotations

import typer
from rich.markdown import Markdown
from rich.panel import Panel

from nexarq_cli.utils.console import console

app = typer.Typer()

_HELP_TEXT = """\
# Nexarq CLI – Quick Reference

## Installation
```bash
pip install nexarq-cli
```

## Setup
```bash
nexarq init                  # Interactive setup wizard
nexarq doctor                # Verify installation
```

## Running a Review
```bash
nexarq run                   # Review last commit (auto-detects language)
nexarq run --agents security,bugs   # Run specific agents
nexarq run --language python        # Force language
nexarq run --diff my.patch          # Review a diff file
nexarq run --list-agents            # See all available agents
```

## Available Agents
| Agent | Focus |
|-------|-------|
| security | OWASP Top 10, secrets, injection |
| bugs | Logic errors, edge cases |
| performance | Complexity, N+1 queries, memory |
| review | Style, naming, best practices |
| architecture | SOLID, design patterns |
| devops | Docker, CI/CD, IaC |
| refactor | DRY, complexity reduction |
| docstring | Missing documentation |
| type_safety | Type annotations, nullable |
| test_coverage | Missing tests, weak assertions |
| dependency | Vulnerable packages, licenses |
| api_design | REST conventions, status codes |
| database | Query safety, migrations |
| concurrency | Race conditions, async |
| error_handling | Exception patterns |
| logging | PII in logs, log levels |
| maintainability | Cyclomatic complexity |
| accessibility | WCAG 2.1, ARIA |
| compliance | GDPR, HIPAA, PCI-DSS |
| explain | Plain-English walkthrough |
| memory_safety | Resource leaks |
| standards | Project-specific rules |

## Configuration
```bash
nexarq config show           # Show current config
nexarq config set-provider ollama --model codellama
nexarq config set-provider openai --model gpt-4o
nexarq config set-key openai          # Store API key securely
nexarq config set-agents security,bugs,review
nexarq config cloud-consent true      # Enable cloud providers
nexarq config add-standards ./STANDARDS.md
```

## Git Hooks
```bash
nexarq hook install post-commit  # Auto-run after every commit
nexarq hook install pre-push     # Run before push
nexarq hook uninstall post-commit
nexarq hook status
```

## MCP Servers
```bash
nexarq mcp add my-scanner http://localhost:8090 --tools scan,analyze
nexarq mcp list
nexarq mcp remove my-scanner
```

## Profiles
```bash
nexarq init --profile work      # Create a work profile
nexarq run --profile work       # Use specific profile
nexarq config list-profiles
```

## Security Notes
- API keys are stored in the system keyring (never plain text)
- Diffs are redacted before cloud sends (SEC-6)
- Cloud providers disabled by default (cloud_consent = false)
- Agents operate on diff-only by default (AG-3)
- Full audit log at ~/.nexarq/logs/

## Getting Help
- Issues: https://github.com/nexarq/nexarq-cli/issues
- Config: ~/.nexarq/config.yaml
- Logs: ~/.nexarq/logs/
"""


@app.command()
def help(
    topic: str = typer.Argument(None, help="Topic: agents, config, hooks, security, mcp"),
) -> None:
    """Show extended help and usage guide."""
    if topic == "agents":
        _help_agents()
    elif topic == "security":
        _help_security()
    elif topic == "config":
        _help_config()
    else:
        console.print(Panel(Markdown(_HELP_TEXT), border_style="blue", padding=(1, 2)))


def _help_agents() -> None:
    from nexarq_cli.agents.registry import REGISTRY
    from rich.table import Table
    from rich import box

    table = Table(title="Nexarq Agents Reference", box=box.ROUNDED, header_style="bold blue")
    table.add_column("Name", style="bold")
    table.add_column("Description")
    table.add_column("Severity")
    table.add_column("Permissions")

    for name in sorted(REGISTRY.names()):
        agent = REGISTRY.get(name)
        sev = str(agent.severity.value if hasattr(agent.severity, "value") else agent.severity)
        perms = []
        if agent.permissions.read_diff_only:
            perms.append("diff-only")
        if agent.permissions.network_access:
            perms.append("network")
        if agent.permissions.mcp_access:
            perms.append("mcp")

        table.add_row(name, agent.description, sev, ", ".join(perms) or "diff-only")

    console.print(table)


def _help_security() -> None:
    text = """\
# Security Architecture

## Data Flow
1. Git diff extracted locally
2. Sensitive data redacted (SEC-6)
3. Cloud consent checked (PR-5/6)
4. Diff sent to provider (never full repo by default)
5. Response validated for injection (SEC-10)
6. Results displayed and logged (SEC-16)

## Key Controls
- **SEC-1/2**: API keys stored in system keyring, never plain text
- **SEC-4**: Local processing by default (Ollama)
- **SEC-5**: Cloud providers require explicit `cloud_consent: true`
- **SEC-6**: Automatic redaction of API keys, tokens, secrets
- **SEC-7/8**: Agents never execute code or shell commands
- **SEC-10**: Prompt injection detection in all LLM outputs
- **AG-3**: Agents only see the diff, not the full repository

## Audit Trail
All actions logged to `~/.nexarq/logs/audit_YYYYMMDD.jsonl`
"""
    console.print(Panel(Markdown(text), title="Security Guide", border_style="red"))


def _help_config() -> None:
    from nexarq_cli.config.manager import NEXARQ_HOME
    text = f"""\
# Configuration Reference

## Location
```
{NEXARQ_HOME}/config.yaml          # Default profile
{NEXARQ_HOME}/profiles/<name>/config.yaml  # Named profiles
```

## Key Fields
- `providers.default`: LLM provider settings
- `default_agents`: Which agents run by default
- `privacy.cloud_consent`: Must be true to use cloud providers
- `git.post_commit`: Enable/disable post-commit hook
- `audit.enabled`: Enable audit logging

## Environment Variables
```
NEXARQ_HOME              Override config directory
NEXARQ_OLLAMA_URL        Override Ollama URL
NEXARQ_OPENAI_API_KEY    OpenAI API key (alternative to keyring)
NEXARQ_ANTHROPIC_API_KEY Anthropic API key
NEXARQ_GOOGLE_API_KEY    Google API key
```
"""
    console.print(Panel(Markdown(text), title="Configuration Guide", border_style="blue"))
