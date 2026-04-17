# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.x (latest) | Yes |

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues privately via GitHub's [Security Advisories](https://github.com/nexarq/nexarq/security/advisories/new) feature. Include:

- A description of the vulnerability and its potential impact
- Steps to reproduce or proof-of-concept code
- Affected versions
- Any suggested fix (optional)

We aim to acknowledge reports within 48 hours and provide a resolution timeline within 7 days.

## Nexarq's own security model

Nexarq is built security-first. Key properties:

- **API keys** are stored in the system keyring (via `keytar`) — never written to disk as plain text
- **Diffs only** — agents never receive the full repository, only the changed lines
- **Redaction before cloud** — secrets, tokens, and credentials are stripped from diffs before any cloud LLM call
- **Cloud opt-in** — all cloud LLM providers are disabled by default (`cloud_consent: false`)
- **Prompt injection defense** — all LLM outputs are validated before being shown to the user or written to disk
- **Audit log** — every agent run is logged locally at `~/.nexarq/logs/`

## Scope

Issues in scope: the CLI, SDK, agent-runtime, web API, and any bundled agent prompts.

Out of scope: vulnerabilities in third-party LLM providers (report these upstream), social engineering, or attacks requiring physical access to the user's machine.
