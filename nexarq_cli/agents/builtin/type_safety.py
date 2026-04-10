"""Type safety agent – missing annotations, type errors, unsafe casts."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a type safety expert specializing in static type analysis.

Analyze the following {language} code diff for type safety issues:
- Missing type annotations on function signatures (Python: missing hints)
- Any/unknown type usage that defeats type checking
- Unsafe type casts or forced assertions (as any, // @ts-ignore)
- Type narrowing errors (accessing attributes that may not exist)
- Nullable type not handled before access
- Return type inconsistencies (sometimes returning None, sometimes value)
- Incorrect use of Optional vs Union types
- Type widening that loses useful type information
- Missing generics where applicable (List vs List[str])

For each issue:
  SEVERITY: [HIGH|MEDIUM|LOW]
  LOCATION: <code snippet>
  ISSUE: <description>
  TYPED VERSION: <corrected code with proper types>

If fully typed: "All types are correctly annotated."

Code diff:
```{language}
{diff}
```"""


class TypeSafetyAgent(BaseAgent):
    name = "type_safety"
    description = "Type annotations, nullable safety, type errors"
    severity = Severity.MEDIUM

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
