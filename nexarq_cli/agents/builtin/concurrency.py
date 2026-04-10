"""Concurrency agent – race conditions, deadlocks, async correctness."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a concurrency and async programming expert.

Analyze the following {language} code diff for concurrency issues:
- Race conditions on shared mutable state
- Deadlock potential (multiple locks acquired in inconsistent order)
- Missing thread synchronization (missing locks, mutex, semaphores)
- Blocking operations inside async functions (time.sleep, requests.get in async)
- Uncancelled async tasks or fire-and-forget without error handling
- Thread-unsafe singletons
- Missing volatile/atomic for flags checked across threads
- Async context manager misuse
- Incorrectly awaited coroutines (missing await)
- Event loop blocking

For each issue:
  SEVERITY: [CRITICAL|HIGH|MEDIUM|LOW]
  LOCATION: <code snippet>
  ISSUE: <description>
  FIX: <thread-safe version>

If no issues: "Concurrency patterns look correct."

Code diff:
```{language}
{diff}
```"""


class ConcurrencyAgent(BaseAgent):
    name = "concurrency"
    description = "Race conditions, deadlocks, async/await correctness"
    severity = Severity.CRITICAL
    needs_tools = True  # searches for shared state and lock patterns across files

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=False, read_full_repo=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
