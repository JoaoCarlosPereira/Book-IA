"""Integration tests: setup → login → protected route → logout."""

import pytest
from httpx import AsyncClient

from app.config import settings
from app.services.auth_service import session_store


@pytest.mark.asyncio
class TestAuthIntegrationFlow:
    async def test_setup_creates_admin_and_session(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/setup",
            data={"login": "admin", "senha": "senha123"},
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 201
        assert settings.session_cookie_name in response.cookies
        assert response.json()["login"] == "admin"

    async def test_login_valid_credentials_sets_cookie(
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

    async def test_protected_route_without_session_redirects(
        self, client: AsyncClient
    ) -> None:
        response = await client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/login"

    async def test_protected_route_with_session_returns_200(
        self, integration_client: AsyncClient
    ) -> None:
        response = await integration_client.get("/dashboard")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    async def test_logout_destroys_session(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/setup",
            data={"login": "admin", "senha": "senha123"},
            headers={"Accept": "application/json"},
        )
        cookie = client.cookies.get(settings.session_cookie_name)
        assert cookie is not None
        assert session_store.validate(cookie) is not None

        logout = await client.post(
            "/api/v1/auth/logout",
            follow_redirects=False,
        )
        assert logout.status_code == 302
        assert logout.headers["location"] == "/login"
        assert session_store.validate(cookie) is None

        protected = await client.get("/dashboard", follow_redirects=False)
        assert protected.status_code == 302

    async def test_full_auth_flow_setup_login_dashboard_logout(
        self, client: AsyncClient
    ) -> None:
        """End-to-end: setup → login → dashboard → logout → blocked."""
        setup = await client.post(
            "/api/v1/auth/setup",
            data={"login": "flowuser", "senha": "flowpass123"},
            headers={"Accept": "application/json"},
        )
        assert setup.status_code == 201

        session_store.clear()
        login = await client.post(
            "/api/v1/auth/login",
            data={"login": "flowuser", "senha": "flowpass123"},
            follow_redirects=False,
        )
        assert login.status_code == 302

        dashboard = await client.get("/dashboard")
        assert dashboard.status_code == 200

        logout = await client.post("/api/v1/auth/logout", follow_redirects=False)
        assert logout.status_code == 302

        blocked = await client.get(
            "/api/v1/livros",
            headers={"Accept": "application/json"},
            follow_redirects=False,
        )
        assert blocked.status_code == 401
