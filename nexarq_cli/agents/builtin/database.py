"""Database agent – query safety, migrations, ORM usage."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a database engineering expert with deep knowledge of SQL, ORMs, and migrations.

Analyze the following {language} code diff for database concerns:
- Raw SQL with string formatting (SQL injection risk)
- Missing transactions for multi-step operations
- Missing rollback handling on failure
- N+1 query patterns in ORM usage
- Missing database indexes for queried columns
- Unsafe migration patterns (dropping columns without deprecation)
- Missing cascade/restrict on foreign keys
- Sensitive data stored without encryption
- Connection pool exhaustion patterns
- Unbounded queries (missing LIMIT)
- Timestamp columns without timezone info

For each issue:
  SEVERITY: [CRITICAL|HIGH|MEDIUM|LOW]
  LOCATION: <query or model>
  ISSUE: <description>
  FIX: <corrected code>

If no issues: "Database code looks safe and efficient."

Code diff:
```{language}
{diff}
```"""


class DatabaseAgent(BaseAgent):
    name = "database"
    description = "Query safety, migrations, ORM patterns, indexes"
    severity = Severity.HIGH

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
