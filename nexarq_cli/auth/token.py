"""Secure token storage in ~/.nexarq/.token (JSON)."""
from __future__ import annotations

import json
from pathlib import Path


class TokenStore:
    _path: Path = Path("~/.nexarq/.token").expanduser()

    @classmethod
    def save(cls, token: str, username: str, scopes: list[str]) -> None:
        cls._path.parent.mkdir(parents=True, exist_ok=True)
        cls._path.write_text(
            json.dumps({"token": token, "username": username, "scopes": scopes}),
            encoding="utf-8",
        )
        # Owner-read only
        try:
            cls._path.chmod(0o600)
        except Exception:
            pass

    @classmethod
    def load(cls) -> dict | None:
        try:
            if cls._path.exists():
                return json.loads(cls._path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return None

    @classmethod
    def clear(cls) -> None:
        cls._path.unlink(missing_ok=True)

    @classmethod
    def token(cls) -> str | None:
        d = cls.load()
        return d["token"] if d else None

    @classmethod
    def username(cls) -> str | None:
        d = cls.load()
        return d["username"] if d else None
