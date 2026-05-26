"""Authentication: password hashing and in-memory session management."""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import bcrypt

from app.config import settings


def hash_password(password: str) -> str:
    """Hash a password with bcrypt (12 rounds by default)."""
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Return True if password matches the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


@dataclass
class SessionData:
    user_id: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SessionStore:
    """In-memory session store with configurable idle timeout."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionData] = {}
        self._lock = threading.Lock()

    @property
    def idle_timeout(self) -> timedelta:
        return timedelta(minutes=settings.session_idle_timeout_minutes)

    def create(self, user_id: int) -> str:
        """Create a session and return its opaque id."""
        session_id = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        with self._lock:
            self._sessions[session_id] = SessionData(
                user_id=user_id,
                created_at=now,
                last_activity=now,
            )
        return session_id

    def validate(self, session_id: str | None) -> int | None:
        """Validate session, refresh idle timer, return user_id or None."""
        if not session_id:
            return None

        now = datetime.now(timezone.utc)
        with self._lock:
            data = self._sessions.get(session_id)
            if data is None:
                return None
            if now - data.last_activity > self.idle_timeout:
                del self._sessions[session_id]
                return None
            data.last_activity = now
            return data.user_id

    def destroy(self, session_id: str | None) -> None:
        """Remove a session from the store."""
        if not session_id:
            return
        with self._lock:
            self._sessions.pop(session_id, None)

    def clear(self) -> None:
        """Remove all sessions (for tests)."""
        with self._lock:
            self._sessions.clear()


session_store = SessionStore()
