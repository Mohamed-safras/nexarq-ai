"""Secure API key storage using the system keyring (SEC-1/2/3)."""
from __future__ import annotations

import base64
import os
from typing import Optional

try:
    import keyring
    _KEYRING_AVAILABLE = True
except ImportError:
    _KEYRING_AVAILABLE = False

try:
    from cryptography.fernet import Fernet
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False

SERVICE_NAME = "nexarq-cli"

# Fallback env-var map when keyring unavailable
_ENV_KEY_MAP: dict[str, str] = {
    "openai": "NEXARQ_OPENAI_API_KEY",
    "anthropic": "NEXARQ_ANTHROPIC_API_KEY",
    "google": "NEXARQ_GOOGLE_API_KEY",
}


class SecretsManager:
    """
    Store/retrieve API keys via system keyring with encrypted fallback.
    Never writes secrets to plain text files (SEC-2).
    """

    def __init__(self) -> None:
        self._fernet: Optional[object] = None  # lazy init

    # ── public API ───────────────────────────────────────────────────────────

    def set_key(self, provider: str, api_key: str) -> None:
        """Store an API key for a provider securely."""
        if _KEYRING_AVAILABLE:
            keyring.set_password(SERVICE_NAME, provider, api_key)
        else:
            self._fallback_set(provider, api_key)

    def get_key(self, provider: str) -> str | None:
        """Retrieve an API key; returns None if not set."""
        # Prefer keyring
        if _KEYRING_AVAILABLE:
            val = keyring.get_password(SERVICE_NAME, provider)
            if val:
                return val

        # Env-var override (convenient for CI)
        env_var = _ENV_KEY_MAP.get(provider)
        if env_var:
            val = os.environ.get(env_var)
            if val:
                return val

        # Encrypted fallback file
        return self._fallback_get(provider)

    def delete_key(self, provider: str) -> None:
        """Remove a stored API key."""
        if _KEYRING_AVAILABLE:
            try:
                keyring.delete_password(SERVICE_NAME, provider)
            except Exception:
                pass
        self._fallback_delete(provider)

    def has_key(self, provider: str) -> bool:
        return self.get_key(provider) is not None

    # ── encrypted file fallback (SEC-3) ──────────────────────────────────────

    def _keyfile_path(self) -> "import pathlib; pathlib.Path":
        from pathlib import Path
        return Path("~/.nexarq/.vault_key").expanduser()

    def _datafile_path(self) -> "import pathlib; pathlib.Path":
        from pathlib import Path
        return Path("~/.nexarq/.vault").expanduser()

    def _get_fernet(self):
        if not _CRYPTO_AVAILABLE:
            return None
        if self._fernet is not None:
            return self._fernet

        from cryptography.fernet import Fernet
        from pathlib import Path

        kf = Path("~/.nexarq/.vault_key").expanduser()
        if kf.exists():
            key = kf.read_bytes()
        else:
            key = Fernet.generate_key()
            kf.parent.mkdir(parents=True, exist_ok=True)
            kf.write_bytes(key)
            kf.chmod(0o600)

        self._fernet = Fernet(key)
        return self._fernet

    def _fallback_set(self, provider: str, api_key: str) -> None:
        f = self._get_fernet()
        if f is None:
            raise RuntimeError(
                "Neither keyring nor cryptography is available. "
                "Install one: pip install keyring  OR  pip install cryptography"
            )
        import json
        from pathlib import Path

        df = Path("~/.nexarq/.vault").expanduser()
        data: dict[str, str] = {}
        if df.exists():
            try:
                data = json.loads(f.decrypt(df.read_bytes()).decode())
            except Exception:
                data = {}

        data[provider] = api_key
        encrypted = f.encrypt(json.dumps(data).encode())
        df.parent.mkdir(parents=True, exist_ok=True)
        df.write_bytes(encrypted)
        df.chmod(0o600)

    def _fallback_get(self, provider: str) -> str | None:
        f = self._get_fernet()
        if f is None:
            return None
        import json
        from pathlib import Path

        df = Path("~/.nexarq/.vault").expanduser()
        if not df.exists():
            return None
        try:
            data = json.loads(f.decrypt(df.read_bytes()).decode())
            return data.get(provider)
        except Exception:
            return None

    def _fallback_delete(self, provider: str) -> None:
        f = self._get_fernet()
        if f is None:
            return
        import json
        from pathlib import Path

        df = Path("~/.nexarq/.vault").expanduser()
        if not df.exists():
            return
        try:
            data = json.loads(f.decrypt(df.read_bytes()).decode())
            data.pop(provider, None)
            df.write_bytes(f.encrypt(json.dumps(data).encode()))
        except Exception:
            pass
