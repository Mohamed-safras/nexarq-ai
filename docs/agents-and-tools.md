# Agents and Tools

## Agent Definition

Every agent is a plain TypeScript object implementing `AgentDefinition` from `@nexarq/common/interfaces`:

```ts
interface AgentDefinition {
  name: string           // kebab-case identifier, e.g. 'security'
  displayName: string    // human display, e.g. 'Security'
  description: string    // one-line summary shown in --list-agents
  severity: Severity     // 'critical' | 'high' | 'medium' | 'low' | 'info'
  tier: AgentTier        // 1 | 2 | 3 (meta)
  needsTools: boolean    // whether agent uses read-only review tools
  systemPrompt: string   // shared prefix (SHARED_SYSTEM_PREFIX)
  buildPrompt: (diff: string, language?: string, context?: string) => string
}
```

All agents share `SHARED_SYSTEM_PREFIX` (structured output instructions + CoT prompt) and call `buildUserPrompt(instructions, diff, language, context)` from `agents/agent-template.ts`.

## All 31 Agents

### Tier 1 — Always Run

| Name | Display | Severity | Description |
|------|---------|----------|-------------|
| `security` | Security | critical | OWASP Top 10, injection flaws, auth issues, sensitive data exposure |
| `secrets` | Secrets | critical | Hardcoded credentials, API keys, tokens, passwords in diffs |
| `bugs` | Bugs | high | Logic errors, null dereferences, off-by-one, unreachable code |
| `performance` | Performance | high | Algorithmic complexity, N+1 queries, unnecessary allocations |
| `review` | Code Review | medium | General code quality, readability, naming, best practices |

### Tier 2 — Context-Selected

| Name | Display | Severity | Description |
|------|---------|----------|-------------|
| `architecture` | Architecture | high | Design patterns, coupling, separation of concerns |
| `api-design` | API Design | high | REST/GraphQL conventions, versioning, error responses |
| `database` | Database | high | Query safety, index usage, migration risks, N+1 |
| `error-handling` | Error Handling | medium | Missing try/catch, swallowed errors, panic propagation |
| `concurrency` | Concurrency | high | Race conditions, deadlocks, unsafe shared state |
| `memory-safety` | Memory Safety | high | Buffer overflows, use-after-free, uninitialized memory |
| `resource-usage` | Resource Usage | medium | File handles, connections, goroutines/threads not closed |
| `type-safety` | Type Safety | medium | `any` usage, unsafe casts, missing type guards |
| `code-smells` | Code Smells | low | God classes, long methods, feature envy, deep nesting |
| `style` | Style | info | Formatting, naming conventions, comment quality |
| `refactor` | Refactor | low | Duplication, extract-method opportunities, simplification |
| `maintainability` | Maintainability | medium | Complexity metrics, testability, dependency injection |
| `dependency` | Dependencies | medium | Vulnerable packages, unnecessary deps, license issues |
| `devops` | DevOps | medium | Dockerfile, CI/CD pipeline, secrets in config files |
| `docstring` | Documentation | info | Missing docstrings, stale comments, API documentation |
| `test-coverage` | Test Coverage | medium | Missing tests for new code, test quality, edge cases |
| `logging` | Logging | low | Log levels, PII in logs, missing audit trails |
| `compliance` | Compliance | high | GDPR, HIPAA, PCI-DSS patterns in code |
| `accessibility` | Accessibility | medium | WCAG 2.1 for HTML/JSX — alt text, ARIA roles, color contrast |
| `i18n` | Internationalization | low | Hardcoded strings, locale handling, RTL support |
| `standards` | Standards | info | Language-specific idioms and community conventions |

### Tier 3 — Meta Agents (Post-Run Synthesis)

| Name | Display | Severity | Description |
|------|---------|----------|-------------|
| `ai-fixes` | AI Fixes | info | Generates concrete fix suggestions for findings |
| `risk-scoring` | Risk Score | high | Aggregates findings into a single risk score with rationale |
| `explain` | Explain | info | Plain-language explanation of what the diff does |
| `summary` | Summary | info | Executive summary of all findings across all agents |
| `next-steps` | Next Steps | info | Prioritized action items based on findings |

## Agent Selection

`selectAgents(triggerSource, diff, config)` in `packages/agent-runtime/src/selector.ts` returns an `AgentSelectionPlan`.

| TriggerSource | Behavior |
|---------------|----------|
| `post-commit` | Tier 1 always, Tier 2 selected by language/diff heuristics |
| `pre-push` | Same as post-commit + blocks on CRITICAL/HIGH findings |
| `pr-review` | All Tier 1 + Tier 2 + all meta agents |
| `on-demand` | Tier 1 + Tier 2 (all) |
| `scheduled` | Same as on-demand |
| `sdk` | Caller-specified agents, else Tier 1 + Tier 2 |
| `coding-agent` | Bypasses review agents entirely — routes to coding-agent graph node |

**Language heuristics:** The selector detects languages from file extensions in the diff and enables relevant Tier 2 agents — e.g., `.sql` files enable `database`, `.html`/`.jsx`/`.tsx` files enable `accessibility`, `.dockerfile` or `docker-compose.yml` enable `devops`.

**User overrides:** `config.agents` (array of agent names) always overrides automatic selection. `config.mode = 'fast'` restricts to Tier 1 only.

## Review Tools (read-only)

Available to Tier 1 and Tier 2 agents when `needsTools: true`:

| Tool | Description |
|------|-------------|
| `read_file` | Read a file's contents (path must be within working directory) |
| `search_code` | Ripgrep-style pattern search across the codebase |
| `list_directory` | List files in a directory with type info |
| `find_references` | Find all references to a symbol across files |
| `git_log` | Read recent git history for a file |

All paths are validated against the working directory — no path traversal.

## Coding Tools (read-write)

Available only when `triggerSource === 'coding-agent'`:

| Tool | Description |
|------|-------------|
| `write_file` | Create or overwrite a file |
| `run_command` | Execute a command from a strict allowlist |
| `git_diff` | Show uncommitted changes |
| `git_status` | Show working tree status |

**Command allowlist** (enforced in `run_command`):
`npm`, `bun`, `tsc`, `eslint`, `prettier`, `jest`, `vitest`, `cargo`, `go`, `python`, `pip`, `mvn`, `gradle`, `make`, `git`

Commands are not run with a shell — arguments are passed as an array to avoid injection.

## Agent Prompt Structure

Every agent prompt follows this structure:

```
[SHARED_SYSTEM_PREFIX]        ← structured output format + CoT instructions
                               (same for all agents)

[Agent-specific instructions] ← what to look for, what to ignore

--- BEGIN DIFF ---
[diff content]
--- END DIFF ---

Language: [detected language or 'Unknown']
[Optional context: PR title, description, file list]

Chain-of-thought: think through the diff first, then produce findings as JSON.
```

Output is a JSON array of `AgentFinding` objects:
```ts
{
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  title: string
  description: string
  file?: string
  line?: number
  suggestion?: string
}
```
