"""Docstring agent – missing documentation detection and generation."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a technical documentation expert.

Review the following {language} code diff and identify ALL functions, classes,
and methods that are missing documentation (docstrings / JSDoc / comments).

For each undocumented item, generate a proper docstring following the language
convention (Google style for Python, JSDoc for JS/TS, Javadoc for Java):
  - One-line summary
  - Args/Parameters section
  - Returns section
  - Raises/Throws section (if applicable)
  - Example (for public APIs)

Output format:
  ITEM: <function/class name>
  LOCATION: <approximate location>
  GENERATED DOCSTRING:
  ```
  <the complete docstring>
  ```

If all items are documented: "All code is properly documented."

Code diff:
```{language}
{diff}
```"""


class DocstringAgent(BaseAgent):
    name = "docstring"
    description = "Missing documentation, docstring generation"
    severity = Severity.LOW

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
