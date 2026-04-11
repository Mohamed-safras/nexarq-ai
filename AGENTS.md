# Nexarq Agents

This is the canonical reference for all agents in the Nexarq system.

## Agent Registry

All agents are defined in `agents/` and registered in `packages/agent-runtime/src/registry.ts`.

## Centralized Agent Architecture

Agents are **shared across all surfaces**:
- CLI (`nexarq run`) — runs agents locally or via API
- Web dashboard — runs agents on PR webhooks or scheduled jobs
- SDK (`@nexarq/sdk`) — runs agents programmatically

Never define agent prompts inside CLI commands or web routes. All agent logic lives in `agents/`.

## Tiers

| Tier | Mode | Agents | When |
|------|------|--------|------|
| 1 | FAST | secrets, security, bugs | Always (pre-push gates, CI) |
| 2 | SMART | 5–12 context-selected agents | Default |
| 3 | DEEP | Tool-augmented, full codebase access | Escalation on CRITICAL/HIGH |

## Available Agents (31)

### Security (Tier 1 — always run)
- `security` — OWASP Top 10, injection, auth flaws (CRITICAL)
- `secrets` — Hardcoded credentials, API keys (CRITICAL)
- `bugs` — Logic errors, null checks, edge cases (HIGH)

### Quality (Tier 2)
- `performance` — N+1 queries, complexity, memory (HIGH)
- `review` — General code quality, best practices (MEDIUM)
- `architecture` — SOLID, coupling, layering (MEDIUM)
- `api_design` — REST/GraphQL/RPC conventions (MEDIUM)
- `database` — SQL injection, schema, indexing (HIGH)
- `error_handling` — Exception patterns, retry logic (MEDIUM)
- `concurrency` — Race conditions, thread safety (HIGH)
- `memory_safety` — Resource leaks, buffer issues (HIGH)
- `resource_usage` — File/connection/memory leaks (MEDIUM)
- `type_safety` — Type annotation completeness (LOW)
- `code_smells` — Design smells, over-engineering (LOW)
- `style` — Naming, formatting conventions (LOW)
- `refactor` — DRY, complexity reduction (LOW)
- `maintainability` — Cyclomatic complexity (MEDIUM)
- `dependency` — Vulnerable packages, updates (HIGH)
- `devops` — Docker, CI/CD, IaC (MEDIUM)

### Documentation and Testing (Tier 2)
- `docstring` — Missing docs, JSDoc, comments (LOW)
- `test_coverage` — Missing test cases (MEDIUM)
- `logging` — PII in logs, log levels (MEDIUM)

### Compliance and Accessibility (Tier 2)
- `compliance` — GDPR, HIPAA, PCI-DSS (HIGH)
- `accessibility` — WCAG 2.1, ARIA (MEDIUM)
- `i18n` — Internationalization, hardcoded strings (LOW)
- `standards` — Project-specific coding standards (LOW)

### Meta-Agents (Tier 2/3)
- `ai_fixes` — Generate AI-powered code fix suggestions (INFO)
- `risk_scoring` — Overall risk assessment score (INFO)
- `explain` — Plain-English walkthrough of changes (INFO)
- `summary` — Executive summary of all findings (INFO)
- `next_steps` — Recommend follow-up actions (INFO)

## Adding a New Agent

1. Create `agents/<name>/index.ts` exporting an `AgentDefinition`
2. Add to `packages/agent-runtime/src/registry.ts`
3. Update this file

## Coding Standards

- Each module in its proper folder
- Naming and variables must be semantically valid
- Agent prompts must be explicit — specify exactly what to look for
- All agents must return findings in the standard `AgentResult` shape
