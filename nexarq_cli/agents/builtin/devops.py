"""DevOps agent – CI/CD, Docker, IaC, deployment safety."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a DevOps and platform engineering expert.

Review the following code diff for DevOps and deployment concerns:
- Hardcoded environment-specific values (should be env vars or config)
- Missing health checks or readiness probes
- Insecure Dockerfile patterns (running as root, ADD vs COPY, latest tags)
- Missing resource limits in container configs
- Secrets passed as environment variables in plain text
- Missing or incorrect .dockerignore / .gitignore entries
- Insecure CI/CD patterns (unrestricted write access, no artifact signing)
- Infrastructure-as-Code security (public S3, open security groups)
- Missing graceful shutdown handling
- Incorrect log levels for production

For each issue:
  SEVERITY: [HIGH|MEDIUM|LOW]
  LOCATION: <snippet or file>
  ISSUE: <description>
  FIX: <recommended change>

If no issues: "No DevOps concerns found."

Code diff:
```{language}
{diff}
```"""


class DevOpsAgent(BaseAgent):
    name = "devops"
    description = "CI/CD, Docker, IaC, deployment and config safety"
    severity = Severity.MEDIUM

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
