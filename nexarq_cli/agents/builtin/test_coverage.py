"""Test coverage agent – missing tests, untested paths, test quality."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a senior QA engineer and testing expert.

Review the following {language} code diff and evaluate test coverage:
- Identify new functions, methods, or classes with no corresponding tests
- Identify edge cases not covered by existing tests
- Check for missing error path testing (exceptions, None returns, empty collections)
- Identify tests that don't actually assert anything meaningful
- Check for test isolation (tests that depend on execution order)
- Missing boundary value tests
- Check for tests using mocks where real implementations should be tested
- Identify flaky test patterns (time-dependent, network-dependent without mocks)

For each gap:
  TYPE: [Missing Test|Untested Edge Case|Weak Assertion|Flaky Pattern]
  ITEM: <function or scenario>
  GAP: <what is not tested>
  SUGGESTED TEST:
  ```{language}
  <example test code>
  ```

If coverage looks complete: "Test coverage appears adequate for the changes."

Code diff:
```{language}
{diff}
```"""


class TestCoverageAgent(BaseAgent):
    name = "test_coverage"
    description = "Missing tests, edge cases, assertion quality"
    severity = Severity.MEDIUM

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
