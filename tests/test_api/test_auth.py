"""Authentication and session tests."""

import bcrypt
import pytest
from httpx import AsyncClient

from app.config import settings
from app.services.auth_service import hash_password, session_store, verify_password


class TestPasswordHashing:
    def test_bcrypt_generates_valid_hash_with_12_rounds(self) -> None:
        password = "senha123"
        hashed = hash_password(password)
        assert hashed.startswith("$2b$12$") or hashed.startswith("$2a$12$")

    def test_verify_password_correct(self) -> None:
        password = "senha123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self) -> None:
        hashed = hash_password("senha123")
        assert verify_password("senha_errada", hashed) is False

    def test_bcrypt_gensalt_12_rounds(self) -> None:
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(b"senha123", salt)
        assert bcrypt.checkpw(b"senha123", hashed)
        assert not bcrypt.checkpw(b"senha_errada", hashed)


@pytest.mark.asyncio
class TestAuthSetup:
    async def test_setup_first_user_returns_201(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/setup",
            data={"login": "admin", "senha": "senha123"},
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["login"] == "admin"
        assert data["perfil"] == "admin"
        assert settings.session_cookie_name in response.cookies

    async def test_setup_second_attempt_returns_403(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/setup",
            data={"login": "admin", "senha": "senha123"},
            headers={"Accept": "application/json"},
        )
        response = await client.post(
            "/api/v1/auth/setup",
            data={"login": "outro", "senha": "senha456"},
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestAuthLogin:
    async def test_login_success_sets_cookie_and_redirects(
        self, client: AsyncClient
    ) -> None:
        await client.post(
            "/api/v1/auth/setup",
            data={"login": "admin", "senha": "senha123"},
            headers={"Accept": "application/json"},
        )
        session_store.clear()

        response = await client.post(
            "/api/v1/auth/login",
            data={"login": "admin", "senha": "senha123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"].endswith("/dashboard")
        assert settings.session_cookie_name in response.cookies

    async def test_login_invalid_credentials_returns_401(
        self, client: AsyncClient
    ) -> None:
        await client.post(
            "/api/v1/auth/setup",
            data={"login": "admin", "senha": "senha123"},
            headers={"Accept": "application/json"},
        )

        response = await client.post(
            "/api/v1/auth/login",
            data={"login": "admin", "senha": "errada"},
            headers={"Accept": "application/json"},
            follow_redirects=False,
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestAuthProtection:
    async def test_protected_route_without_session_redirects_to_login(
        self, client: AsyncClient
    ) -> None:
        response = await client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/login"

    async def test_protected_route_with_session_returns_200(
        self, client: AsyncClient
    ) -> None:
        await client.post(
            "/api/v1/auth/setup",
            data={"login": "admin", "senha": "senha123"},
            headers={"Accept": "application/json"},
        )
        response = await client.get("/dashboard")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert b"admin" in response.content or b"Book-IA" in response.content


@pytest.mark.asyncio
class TestAuthLogout:
    async def test_logout_clears_session_and_redirects(
        self, client: AsyncClient
    ) -> None:
        await client.post(
            "/api/v1/auth/setup",
            data={"login": "admin", "senha": "senha123"},
            headers={"Accept": "application/json"},
        )
        cookie = client.cookies.get(settings.session_cookie_name)
        assert cookie is not None
        assert session_store.validate(cookie) is not None

        response = await client.post(
            "/api/v1/auth/logout",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/login"
        assert session_store.validate(cookie) is None

        protected = await client.get("/dashboard", follow_redirects=False)
        assert protected.status_code == 302


@pytest.mark.asyncio
async def test_login_page_renders_html(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Book-IA" in response.text
