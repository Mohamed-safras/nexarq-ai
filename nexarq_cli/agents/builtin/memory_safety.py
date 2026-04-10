"""Memory safety agent – leaks, unbounded growth, buffer issues."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a memory safety and resource management expert.

Analyze the following {language} code diff for memory and resource issues:
- File handles opened but not closed (missing close() or context manager)
- Database connections not returned to pool
- Large objects accumulated in memory without cleanup
- Unbounded lists/dicts that grow indefinitely (potential OOM)
- Event listeners/callbacks registered but never removed
- Circular references preventing garbage collection
- Large file loaded entirely into memory (should stream instead)
- Regex patterns not compiled and cached (recompiled on every call)
- Thread-local storage not cleaned up
- Buffer overruns in low-level code (C extensions, ctypes)

For each issue:
  SEVERITY: [HIGH|MEDIUM|LOW]
  LOCATION: <code snippet>
  ISSUE: <description>
  FIX: <resource-safe version>

If no issues: "Resource management looks correct."

Code diff:
```{language}
{diff}
```"""


class MemorySafetyAgent(BaseAgent):
    name = "memory_safety"
    description = "Resource leaks, unbounded growth, unclosed handles"
    severity = Severity.HIGH
    needs_tools = True  # reads full files to trace resource lifecycle

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=False, read_full_repo=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
