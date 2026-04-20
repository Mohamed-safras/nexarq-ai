# Feature Testing Guide

Step-by-step verification for every Nexarq feature. Run these after setup or after significant changes.

## Prerequisites

```bash
# 1. Install dependencies
bun install

# 2. Set at least one LLM provider key (Anthropic recommended)
export NEXARQ_ANTHROPIC_API_KEY=sk-ant-...

# 3. Optional — enable web search and docs
export NEXARQ_BRAVE_API_KEY=BSA...

# 4. Build / link the CLI locally
cd cli && bun link
```

---

## 1. Interactive REPL (default `nexarq`)

```bash
nexarq
```

**Expect:** Gradient ASCII logo, version line, prompt `nexarq ›`

| Input | Expected output |
|-------|----------------|
| `help` | Command table printed |
| `hello, what can you do?` | Assistant describes capabilities |
| `exit` | "Goodbye." and clean exit |

**Session persistence check:**
```bash
nexarq        # ask something
# Ctrl+C exit
nexarq        # re-open
# Ask a follow-up — it should remember the previous turn
```

---

## 2. Code Review — `nexarq run`

Make a change in a git repo, then:
```bash
# Review uncommitted changes
nexarq run

# Review a specific diff file
nexarq run --diff path/to/file.diff

# Fast mode (tier 1 only — security, secrets, bugs)
nexarq run --mode fast

# Target specific agents
nexarq run --agents security,bugs,type_safety

# List all available agents
nexarq run --list-agents
```

**Expect:** TUI with agent progress bars, then detailed report sorted by severity.

---

## 3. Parallel Coding Team — `nexarq code`

```bash
nexarq code "Add input validation to the createUser function"
```

**Expect:**
- TUI shows planner → parallel coders → reviewer stages
- Summary lists modified files and reviewer notes

```bash
# Specify a directory
nexarq code "Add logging middleware" --dir ./packages/api
```

---

## 4. Chat TUI — `nexarq chat`

```bash
nexarq chat
```

**Expect:** Full-screen TUI with input box at bottom.

| Action | Expected |
|--------|----------|
| Type a question, press Enter | Nexarq replies in the body area |
| Ask "review my code" | Triggers a diff review inline |
| Ask follow-up | Conversation context retained within the session |

---

## 5. Conversation Orchestrator (all tools in REPL)

Start `nexarq` and test each tool category:

### Code review via chat
```
nexarq › review my current changes
```
Expect: triggers `trigger_review`, returns severity counts + top findings.

### Implement a task via chat
```
nexarq › add a rate limiter to the /api/login route
```
Expect: calls `implement_task`, shows subtasks completed + modified files.

### Web search
```
nexarq › search for express rate limiting best practices
```
Expect: calls `web_search`, returns top Brave results. (Requires `NEXARQ_BRAVE_API_KEY`)

### Docs lookup
```
nexarq › show me how to use drizzle ORM's schema builder
```
Expect: fetches drizzle docs via Brave + Jina, returns relevant section.

### Browser automation
```
nexarq › open https://docs.anthropic.com and summarize the page
```
Expect: calls `open_page`, returns page text summary. (Requires `playwright` installed)

### Shell execution (unsafe mode)
```bash
# Enable in config first
nexarq config set unsafeShell true

nexarq › install the zod package
```
Expect: calls `run_shell` with `bun add zod`, returns install output.

---

## 6. Git Hooks

```bash
# Install hooks
nexarq hook install

# Verify hooks exist
ls .git/hooks/post-commit .git/hooks/pre-push

# Test post-commit (review after commit)
git add . && git commit -m "test commit"
# Expect: review runs automatically after commit

# Test pre-push gate
git push
# If CRITICAL/HIGH findings: push is blocked with explanation

# Skip review for a single commit
NEXARQ_SKIP=1 git commit -m "skip review"
```

---

## 7. Explain — `nexarq explain`

```bash
nexarq explain src/index.ts
nexarq explain src/auth.ts:42-80
```
Expect: Plain-English walkthrough of the file or line range.

---

## 8. Watch Mode — `nexarq watch`

```bash
nexarq watch
```
Expect: "Watching for changes..." — make a file edit and save, review triggers automatically.

---

## 9. Fix — `nexarq fix`

```bash
# After nexarq run finds issues
nexarq fix
```
Expect: AI-suggested patches presented with accept/reject prompt.

---

## 10. Commit Message — `nexarq commit`

```bash
git add .
nexarq commit
```
Expect: AI-generated commit message presented for confirmation.

---

## 11. Extended Thinking Agent (deep analysis)

```bash
nexarq run --agents deep_analysis --mode deep
```
Expect: deep_analysis agent runs with extended thinking (Claude Sonnet only), more detailed security findings.

---

## 12. Config & Setup

```bash
# Show current config
nexarq config

# Set a value
nexarq config set theme dark
nexarq config set provider anthropic
nexarq config set unsafeShell false

# Health check — verifies provider, git, hooks, node version
nexarq doctor
```

---

## 13. SDK Programmatic Use

```ts
import { runOrchestrator, runConversationTurn } from '@nexarq/agent-runtime'

// One-shot review
const result = await runOrchestrator({
  diffResult: { rawDiff, files: [], ... },
  triggerSource: 'sdk',
  workingDirectory: process.cwd(),
  runConfig: { provider: 'anthropic', mode: 'smart' },
})
console.log(result.summary) // { critical, high, medium, low, info }

// Conversation turn (with persistent session)
const turn = await runConversationTurn({
  userMessage: 'review my changes',
  workingDirectory: process.cwd(),
  runConfig: { provider: 'anthropic' },
})
console.log(turn.response)
console.log(turn.suggestedFollowups) // ['Fix SQL injection in auth.ts', ...]
```

---

## 14. Environment Variable Verification

```bash
nexarq doctor
```

Should report:
- `provider` key found  
- `git` repository detected  
- Hooks installed (if applicable)
- `NEXARQ_BRAVE_API_KEY` set (optional, for web search)
- `NEXARQ_JINA_API_KEY` set (optional, for higher doc-fetch rate limits)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `No provider configured` | Run `nexarq init` or set `NEXARQ_ANTHROPIC_API_KEY` |
| `web_search unavailable` | Set `NEXARQ_BRAVE_API_KEY` |
| `Playwright not installed` | Run `npx playwright install chromium` |
| `No diff found` | Ensure you have uncommitted changes or specify `--diff` |
| `Push blocked` | Fix CRITICAL/HIGH findings, or `NEXARQ_SKIP=1 git push` |
| Session history growing too large | Delete `.nexarq/session.json` to reset |
