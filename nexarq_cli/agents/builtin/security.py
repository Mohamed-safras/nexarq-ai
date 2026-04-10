"""Security agent – OWASP Top 10 + secrets + injection scanning."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a senior application security engineer performing a security audit.

Analyze the following {language} code diff for:
- SQL injection (parameterised query violations)
- XSS – unescaped output rendered in HTML/JS
- Hardcoded secrets, API keys, tokens, or credentials
- OWASP Top 10 vulnerabilities (A01-A10:2021)
- Insecure cryptography (MD5/SHA1 for passwords, hardcoded salts, weak IV)
- Insecure deserialisation (eval, exec, pickle.loads, yaml.load without Loader)
- Path traversal and directory listing
- SSRF (unvalidated URLs passed to HTTP clients)
- Command injection (shell=True, os.system with user input)
- Authentication/authorisation bypass patterns

For EACH finding output:
  SEVERITY: [CRITICAL|HIGH|MEDIUM|LOW]
  LOCATION: <file or code snippet reference>
  VULNERABILITY: <name>
  DESCRIPTION: <what is wrong>
  ATTACK VECTOR: <how it could be exploited>
  FIX: <secure replacement code>

If no vulnerabilities found: "No security vulnerabilities found."

Code diff to analyze:
```{language}
{diff}
```"""


class SecurityAgent(BaseAgent):
    name = "security"
    description = "OWASP Top 10 + secrets detection + injection scanning"
    severity = Severity.CRITICAL
    needs_tools = True  # searches for vulnerability patterns across the repo

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=False, read_full_repo=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
