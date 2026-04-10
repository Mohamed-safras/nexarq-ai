"""Resource usage agent – memory, CPU, file handles, and connection leak detection."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a systems performance engineer specializing in resource management.

Analyze the following {language} code diff for resource usage issues:

MEMORY:
- Memory leaks (objects allocated but never freed/garbage collected)
- Large object creation in loops
- Unbounded caches or growing collections
- Missing buffer limits on I/O reads
- Reference cycles preventing GC

CPU:
- O(n²) or worse algorithms where O(n log n) exists
- Unnecessary repeated computation (missing memoization)
- Busy-wait loops (while True: check_condition() with no sleep)
- Blocking operations on main/UI thread
- Regex compilation inside hot loops

I/O RESOURCES:
- File handles opened but not closed (missing try/finally or context managers)
- Database connections not returned to pool
- Network sockets not properly closed
- Missing timeouts on blocking I/O

CONCURRENCY RESOURCES:
- Thread pool exhaustion (unbounded task submission)
- Lock held during I/O (prevents concurrent access)
- Missing connection pool limits

For EACH issue:
  RESOURCE TYPE: <memory|cpu|io|concurrency>
  SEVERITY: [CRITICAL|HIGH|MEDIUM|LOW]
  LOCATION: <reference>
  ISSUE: <description of the resource problem>
  IMPACT: <what happens under load>
  FIX: <recommended solution>

If no issues found: "No resource management issues detected."

Code diff:
```{language}
{diff}
```"""


class ResourceUsageAgent(BaseAgent):
    name = "resource_usage"
    description = "Memory leaks, CPU hotspots, and I/O resource management analysis"
    severity = Severity.HIGH

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
