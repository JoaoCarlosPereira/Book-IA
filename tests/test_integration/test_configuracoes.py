"""Integration tests: API config CRUD and connection testing (mocked httpx)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.api_config import ApiConfig
from app.services.api_config_service import decrypt_token


@pytest.mark.asyncio
class TestConfiguracoesIntegration:
    async def _create(
        self, client: AsyncClient, **kwargs: object
    ) -> dict:
        payload = {
            "tipo": "llm",
            "modo": "cloud",
            "url": "https://generativelanguage.googleapis.com",
            "token": "secret-integration-key",
            "modelo": "gemini-2.0-flash",
            **kwargs,
        }
        resp = await client.post("/api/v1/configuracoes/apis", json=payload)
        assert resp.status_code == 201
        return resp.json()

    async def test_crud_completo_api_config(
        self, integration_client: AsyncClient, db_session
    ) -> None:
        created = await self._create(integration_client)
        config_id = created["id"]
        assert created["token"] == "***"
        assert created["tipo"] == "llm"

        listed = await integration_client.get("/api/v1/configuracoes/apis")
        assert listed.status_code == 200
        assert len(listed.json()) == 1
        assert listed.json()[0]["token"] == "***"

        updated = await integration_client.put(
            f"/api/v1/configuracoes/apis/{config_id}",
            json={"modelo": "gemini-1.5-pro", "modo": "local"},
        )
        assert updated.status_code == 200
        assert updated.json()["modelo"] == "gemini-1.5-pro"

        row = (
            await db_session.execute(
                select(ApiConfig).where(ApiConfig.id == config_id)
            )
        ).scalar_one()
        assert decrypt_token(row.token) == "secret-integration-key"

        deleted = await integration_client.delete(
            f"/api/v1/configuracoes/apis/{config_id}"
        )
        assert deleted.status_code == 204

        await db_session.refresh(row)
        assert row.ativo is False

        list_active = await integration_client.get("/api/v1/configuracoes/apis")
        assert list_active.json() == []

    async def test_testar_conexao_url_valida(
        self, integration_client: AsyncClient
    ) -> None:
        created = await self._create(
            integration_client,
            tipo="tts",
            modo="local",
            url="http://localhost:8001/health",
            token=None,
        )
        config_id = created["id"]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.services.api_config_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            resp = await integration_client.post(
                f"/api/v1/configuracoes/apis/{config_id}/testar",
                headers={"Accept": "application/json"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["conectado"] is True
        assert isinstance(data["latencia_ms"], int)

    async def test_testar_conexao_url_invalida(
        self, integration_client: AsyncClient
    ) -> None:
        created = await self._create(
            integration_client,
            url="http://host-que-nao-existe.invalid/ping",
            token=None,
        )
        config_id = created["id"]

        resp = await integration_client.post(
            f"/api/v1/configuracoes/apis/{config_id}/testar",
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["conectado"] is False
        assert data["erro"]

    async def test_configuracoes_requer_autenticacao(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get(
            "/api/v1/configuracoes/apis",
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 401
