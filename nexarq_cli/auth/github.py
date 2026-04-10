"""
GitHub Device Flow OAuth for Nexarq CLI.

Flow:
  1. POST /login/device/code  → device_code, user_code, verification_uri, interval
  2. Build full auth URL (verification_uri_complete or uri?user_code=XXX)
  3. Show URL to user, poll /login/oauth/access_token in background
  4. On success, fetch /user, store token + username

Scopes requested: read:user, repo (for private repo context, optional)

Client ID: set NEXARQ_GITHUB_CLIENT_ID env var or configure in ~/.nexarq/config.yaml.
           Leave blank to skip GitHub login.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable

import httpx


# ── Default OAuth App ─────────────────────────────────────────────────────────
# Priority order:
#   1. env var  NEXARQ_GITHUB_CLIENT_ID
#   2. ~/.nexarq/config.yaml  →  github_client_id
# Device flow client_id is public (not secret — only the token is).
def _load_client_id() -> str:
    env = os.environ.get("NEXARQ_GITHUB_CLIENT_ID", "")
    if env:
        return env
    try:
        from nexarq_cli.config.manager import ConfigManager
        cfg = ConfigManager().load()
        return cfg.github_client_id or ""
    except Exception:
        return ""

_DEFAULT_CLIENT_ID = _load_client_id()

_SCOPE = "read:user"
_DEVICE_CODE_URL  = "https://github.com/login/device/code"
_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
_USER_URL         = "https://api.github.com/user"


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class DeviceCodeResponse:
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str   # pre-filled URL (may be same as above)
    expires_in: int                  # seconds
    interval: int                    # polling interval in seconds


@dataclass
class LoginResult:
    token: str
    username: str
    name: str
    scopes: list[str]


# ── Main class ────────────────────────────────────────────────────────────────

class GitHubAuth:
    """
    GitHub Device Flow authentication.

    Usage:
        auth = GitHubAuth()
        dc = auth.request_device_code()
        # Show dc.verification_uri_complete to user
        result = auth.poll_for_token(dc, on_waiting=lambda: None)
        TokenStore.save(result.token, result.username, result.scopes)
    """

    def __init__(self, client_id: str = "") -> None:
        self._client_id = client_id or _DEFAULT_CLIENT_ID
        if not self._client_id:
            raise RuntimeError(
                "No GitHub OAuth client_id configured.\n"
                "Set NEXARQ_GITHUB_CLIENT_ID or add github_client_id to ~/.nexarq/config.yaml"
            )

    def request_device_code(self) -> DeviceCodeResponse:
        """Step 1: Request a device code from GitHub."""
        resp = httpx.post(
            _DEVICE_CODE_URL,
            data={"client_id": self._client_id, "scope": _SCOPE},
            headers={"Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            raise RuntimeError(f"GitHub error: {data.get('error_description', data['error'])}")

        uri = data.get("verification_uri", "https://github.com/login/device")
        user_code = data.get("user_code", "")
        complete = data.get(
            "verification_uri_complete",
            f"{uri}?user_code={user_code}",
        )

        return DeviceCodeResponse(
            device_code=data["device_code"],
            user_code=user_code,
            verification_uri=uri,
            verification_uri_complete=complete,
            expires_in=int(data.get("expires_in", 900)),
            interval=int(data.get("interval", 5)),
        )

    def poll_for_token(
        self,
        dc: DeviceCodeResponse,
        on_waiting: Callable[[], None] | None = None,
    ) -> LoginResult:
        """
        Step 2: Poll GitHub until the user completes auth or the code expires.

        Raises RuntimeError on access_denied, expired, or network failure.
        Calls on_waiting() on each polling tick so the caller can animate UI.
        """
        deadline = time.monotonic() + dc.expires_in
        interval = dc.interval

        while time.monotonic() < deadline:
            if on_waiting:
                on_waiting()

            time.sleep(interval)

            resp = httpx.post(
                _ACCESS_TOKEN_URL,
                data={
                    "client_id":   self._client_id,
                    "device_code": dc.device_code,
                    "grant_type":  "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            error = data.get("error", "")

            if error == "authorization_pending":
                continue
            elif error == "slow_down":
                interval += 5
                continue
            elif error == "access_denied":
                raise RuntimeError("Login cancelled — access denied.")
            elif error == "expired_token":
                raise RuntimeError("Login link expired. Run nexarq login again.")
            elif error:
                raise RuntimeError(f"GitHub error: {data.get('error_description', error)}")

            token = data.get("access_token", "")
            if token:
                scopes = [s.strip() for s in data.get("scope", "").split(",") if s.strip()]
                username, name = self._fetch_user(token)
                return LoginResult(token=token, username=username, name=name, scopes=scopes)

        raise RuntimeError("Login timed out. Run nexarq login again.")

    def _fetch_user(self, token: str) -> tuple[str, str]:
        """Fetch GitHub username and display name."""
        try:
            resp = httpx.get(
                _USER_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("login", "unknown"), data.get("name") or data.get("login", "")
        except Exception:
            return "unknown", ""
