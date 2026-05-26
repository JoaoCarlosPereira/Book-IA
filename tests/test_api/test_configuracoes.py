"""Tests for API configuration CRUD and connection testing."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient, Response
from pydantic import ValidationError

from app.schemas.api_config import ApiConfigCreate, ApiConfigUpdate
from app.services.api_config_service import (
    decrypt_token,
    encrypt_token,
    probe_url_connection,
)


class TestFernetEncryption:
    def test_encrypt_decrypt_round_trip(self) -> None:
        plain = "token123"
        encrypted = encrypt_token(plain)
        assert encrypted != plain
        assert decrypt_token(encrypted) == plain

    def test_fernet_encrypt_bytes_directly(self) -> None:
        key = Fernet.generate_key()
        f = Fernet(key)
        token = f.encrypt(b"token123")
        assert f.decrypt(token) == b"token123"


class TestSchemaValidation:
    def test_tipo_accepts_valid_values(self) -> None:
        for tipo in ("llm", "tts", "musicgen"):
            cfg = ApiConfigCreate(tipo=tipo, modo="cloud", url="http://example.com")
            assert cfg.tipo == tipo

    def test_tipo_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ApiConfigCreate(tipo="invalid", modo="cloud", url="http://example.com")  # type: ignore[arg-type]

    def test_modo_accepts_valid_values(self) -> None:
        for modo in ("cloud", "local"):
            cfg = ApiConfigCreate(tipo="llm", modo=modo, url="http://example.com")
            assert cfg.modo == modo

    def test_modo_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ApiConfigCreate(tipo="llm", modo="invalid", url="http://example.com")  # type: ignore[arg-type]

    def test_update_partial_fields(self) -> None:
        upd = ApiConfigUpdate(url="http://new.example.com")
        assert upd.url == "http://new.example.com"
        assert upd.tipo is None


@pytest.mark.asyncio
class TestConfiguracoesCRUD:
    async def _create(self, client: AsyncClient, **kwargs: object) -> Response:
        payload = {
            "tipo": "llm",
            "modo": "cloud",
            "url": "https://generativelanguage.googleapis.com",
            "token": "secret-api-key",
            "modelo": "gemini-2.0-flash",
            **kwargs,
        }
        return await client.post("/api/v1/configuracoes/apis", json=payload)

    async def test_create_encrypts_token(
        self, authenticated_client: AsyncClient, db_session
    ) -> None:
        client = authenticated_client
        from sqlalchemy import select

        from app.models.api_config import ApiConfig

        response = await self._create(client)
        assert response.status_code == 201
        data = response.json()
        assert data["token"] == "***"
        assert data["tipo"] == "llm"

        result = await db_session.execute(select(ApiConfig))
        row = result.scalars().first()
        assert row is not None
        assert row.token != "secret-api-key"
        assert decrypt_token(row.token) == "secret-api-key"

    async def test_list_masks_token(self, authenticated_client: AsyncClient) -> None:
        client = authenticated_client
        await self._create(client)
        response = await client.get("/api/v1/configuracoes/apis")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["token"] == "***"

    async def test_update_config(self, authenticated_client: AsyncClient) -> None:
        client = authenticated_client
        created = await self._create(client)
        config_id = created.json()["id"]
        response = await client.put(
            f"/api/v1/configuracoes/apis/{config_id}",
            json={"modelo": "gemini-1.5-pro", "modo": "local"},
        )
        assert response.status_code == 200
        assert response.json()["modelo"] == "gemini-1.5-pro"
        assert response.json()["modo"] == "local"

    async def test_delete_soft_sets_inativo(
        self, authenticated_client: AsyncClient, db_session
    ) -> None:
        client = authenticated_client
        from sqlalchemy import select

        from app.models.api_config import ApiConfig

        created = await self._create(client)
        config_id = created.json()["id"]

        delete_resp = await client.delete(f"/api/v1/configuracoes/apis/{config_id}")
        assert delete_resp.status_code == 204

        result = await db_session.execute(
            select(ApiConfig).where(ApiConfig.id == config_id)
        )
        row = result.scalar_one()
        assert row.ativo is False

        list_resp = await client.get("/api/v1/configuracoes/apis")
        assert list_resp.json() == []

        list_all = await client.get(
            "/api/v1/configuracoes/apis",
            params={"incluir_inativos": "true"},
        )
        assert len(list_all.json()) == 1
        assert list_all.json()[0]["ativo"] is False

    async def test_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/configuracoes/apis",
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestConfiguracoesTestar:
    async def test_testar_success(self, authenticated_client: AsyncClient) -> None:
        client = authenticated_client
        created = await client.post(
            "/api/v1/configuracoes/apis",
            json={
                "tipo": "tts",
                "modo": "local",
                "url": "http://localhost:8001/health",
            },
        )
        config_id = created.json()["id"]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch(
            "app.services.api_config_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            response = await client.post(
                f"/api/v1/configuracoes/apis/{config_id}/testar"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["conectado"] is True
        assert isinstance(data["latencia_ms"], int)

    async def test_testar_invalid_url(self, authenticated_client: AsyncClient) -> None:
        client = authenticated_client
        created = await client.post(
            "/api/v1/configuracoes/apis",
            json={
                "tipo": "llm",
                "modo": "cloud",
                "url": "http://invalid-host-that-does-not-exist.local/ping",
            },
        )
        config_id = created.json()["id"]

        response = await client.post(
            f"/api/v1/configuracoes/apis/{config_id}/testar"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["conectado"] is False
        assert data["erro"]

    async def test_test_url_connection_unit(self) -> None:
        import httpx

        with patch(
            "app.services.api_config_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection failed"))
            mock_client_cls.return_value = mock_client

            result = await probe_url_connection("http://bad.example")

        assert result.conectado is False
        assert result.erro is not None
