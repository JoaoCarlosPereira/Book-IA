"""Unit tests for auth_service (bcrypt wrappers and session store)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.auth_service import (
    SessionStore,
    hash_password,
    session_store,
    verify_password,
)


class TestHashPassword:
    @patch("app.services.auth_service.bcrypt.gensalt")
    @patch("app.services.auth_service.bcrypt.hashpw")
    def test_hash_password_calls_bcrypt(
        self, mock_hashpw: MagicMock, mock_gensalt: MagicMock
    ) -> None:
        mock_gensalt.return_value = b"$2b$12$saltsaltsaltsalt"
        mock_hashpw.return_value = b"$2b$12$hashedpasswordbytesxx"

        result = hash_password("minha_senha")

        mock_gensalt.assert_called_once()
        mock_hashpw.assert_called_once_with(b"minha_senha", b"$2b$12$saltsaltsaltsalt")
        assert result == "$2b$12$hashedpasswordbytesxx"

    def test_hash_password_produces_valid_bcrypt_hash(self) -> None:
        hashed = hash_password("senha123")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")


class TestVerifyPassword:
    @patch("app.services.auth_service.bcrypt.checkpw")
    def test_verify_password_correct(self, mock_checkpw: MagicMock) -> None:
        mock_checkpw.return_value = True
        assert verify_password("senha", "$2b$12$hash") is True
        mock_checkpw.assert_called_once_with(b"senha", b"$2b$12$hash")

    @patch("app.services.auth_service.bcrypt.checkpw")
    def test_verify_password_incorrect(self, mock_checkpw: MagicMock) -> None:
        mock_checkpw.return_value = False
        assert verify_password("errada", "$2b$12$hash") is False

    def test_verify_password_rejects_invalid_hash(self) -> None:
        assert verify_password("senha", "nao-e-hash-bcrypt") is False

    def test_verify_password_accepts_real_hash(self) -> None:
        hashed = hash_password("senha123")
        assert verify_password("senha123", hashed) is True
        assert verify_password("outra", hashed) is False


class TestSessionStore:
    def setup_method(self) -> None:
        session_store.clear()

    def teardown_method(self) -> None:
        session_store.clear()

    def test_create_and_validate_returns_user_id(self) -> None:
        session_id = session_store.create(user_id=42)
        assert isinstance(session_id, str)
        assert session_store.validate(session_id) == 42

    def test_validate_none_or_unknown_returns_none(self) -> None:
        assert session_store.validate(None) is None
        assert session_store.validate("sessao-inexistente") is None

    def test_destroy_removes_session(self) -> None:
        session_id = session_store.create(user_id=1)
        session_store.destroy(session_id)
        assert session_store.validate(session_id) is None

    def test_idle_timeout_expires_session(self) -> None:
        store = SessionStore()
        session_id = store.create(user_id=7)
        with store._lock:
            data = store._sessions[session_id]
            data.last_activity = datetime.now(timezone.utc) - timedelta(hours=2)
        assert store.validate(session_id) is None

    def test_clear_removes_all_sessions(self) -> None:
        session_store.create(user_id=1)
        session_store.create(user_id=2)
        session_store.clear()
        assert not session_store._sessions

    def test_validate_refreshes_last_activity(self) -> None:
        session_id = session_store.create(user_id=99)
        with session_store._lock:
            before = session_store._sessions[session_id].last_activity
        session_store.validate(session_id)
        with session_store._lock:
            after = session_store._sessions[session_id].last_activity
        assert after >= before
