"""Secrets detection agent – dedicated high-sensitivity secret scanner."""
from nexarq_cli.agents.base import BaseAgent, AgentPermissions, Severity

_PROMPT = """\
You are a secrets detection specialist. Your ONLY job is to find exposed secrets and credentials.

Scan the following code diff for ANY exposed secrets, credentials, or sensitive data:

SECRET CATEGORIES TO SCAN:
- API Keys: AWS (AKIA...), GCP, Azure, Stripe (sk_live/sk_test), Twilio, SendGrid, GitHub PATs
- Credentials: username/password pairs, database connection strings with passwords
- Tokens: JWT tokens, OAuth tokens, session tokens, bearer tokens
- Private Keys: RSA/EC/DSA private keys (-----BEGIN ... PRIVATE KEY-----)
- Certificates: Client certificates embedded in code
- Cloud secrets: AWS secret access keys, Azure storage keys, GCP service account JSON
- Encryption keys: hardcoded symmetric keys, IVs, salts
- Webhook secrets, Slack tokens, Discord tokens
- SSH private keys or passphrases

For EACH secret found output:
  SEVERITY: CRITICAL
  TYPE: <secret type>
  LOCATION: <file:line if available>
  PATTERN: <sanitized pattern showing how it was detected – do NOT reproduce the full secret>
  IMMEDIATE ACTION: <what to do right now>
  REMEDIATION: <long-term fix>

IMPORTANT: Do NOT reproduce the actual secret value in your output – only describe the type and location.

If no secrets found: "No secrets or credentials detected in this diff."

Code diff:
```{language}
{diff}
```"""


class SecretsDetectionAgent(BaseAgent):
    name = "secrets_detection"
    description = "Dedicated high-sensitivity scanner for exposed secrets and credentials"
    severity = Severity.CRITICAL

    def __init__(self) -> None:
        super().__init__()
        self.permissions = AgentPermissions(read_diff_only=True)

    def build_prompt(self, diff: str, language: str, context: dict | None = None) -> str:
        return _PROMPT.format(language=language, diff=diff)
