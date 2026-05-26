"""Integration tests: HTMX partial HTML responses via TestClient."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.book_task import BookTask
from app.models.livro import Livro
from tests.conftest import HTMX_HEADERS
from tests.test_integration.conftest import pdf_upload, upload_file


@pytest.mark.asyncio
class TestHtmxIntegration:
    async def test_progresso_polling_returns_html_partial(
        self, integration_client: AsyncClient, db_session
    ) -> None:
        livro = Livro(
            titulo="HTMX Prog",
            nome_arquivo="h.pdf",
            tipo_documento="pdf",
            nivel_producao="basico",
            status="processando",
            progresso=0,
            usuario_id=1,
        )
        db_session.add(livro)
        await db_session.flush()
        db_session.add(
            BookTask(
                livro_id=livro.id,
                status="processando",
                prioridade=5,
                progresso=55,
                etapa_atual="IA_ANALYSIS",
            )
        )
        await db_session.commit()

        resp = await integration_client.get(
            f"/api/v1/livros/{livro.id}/progresso",
            headers=HTMX_HEADERS,
        )
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "progress-bar" in resp.text
        assert "55%" in resp.text
        assert "IA_ANALYSIS" in resp.text

    async def test_upload_htmx_returns_success_partial(
        self, integration_client: AsyncClient
    ) -> None:
        name, data, ctype = pdf_upload()
        resp = await upload_file(
            integration_client, name, data, ctype, htmx=True
        )
        assert resp.status_code in (200, 201)
        assert "text/html" in resp.headers["content-type"]
        assert "sucesso" in resp.text.lower() or "success" in resp.text.lower()

    async def test_livro_list_htmx_returns_partial(
        self, integration_client: AsyncClient, db_session
    ) -> None:
        livro = Livro(
            titulo="Lista HTMX",
            nome_arquivo="l.pdf",
            tipo_documento="pdf",
            nivel_producao="basico",
            status="pendente",
            progresso=0,
            usuario_id=1,
        )
        db_session.add(livro)
        await db_session.flush()
        db_session.add(
            BookTask(
                livro_id=livro.id,
                status="pendente",
                prioridade=5,
                progresso=0,
            )
        )
        await db_session.commit()

        resp = await integration_client.get(
            "/api/v1/livros",
            headers=HTMX_HEADERS,
        )
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Lista HTMX" in resp.text or "livro" in resp.text.lower()

    async def test_pausar_htmx_returns_livro_card_partial(
        self, integration_client: AsyncClient, db_session
    ) -> None:
        livro = Livro(
            titulo="Card HTMX",
            nome_arquivo="c.pdf",
            tipo_documento="pdf",
            nivel_producao="basico",
            status="processando",
            progresso=10,
            usuario_id=1,
        )
        db_session.add(livro)
        await db_session.flush()
        db_session.add(
            BookTask(
                livro_id=livro.id,
                status="processando",
                prioridade=5,
                progresso=10,
                etapa_atual="ia",
                celery_task_id="t-1",
            )
        )
        await db_session.commit()

        resp = await integration_client.post(
            f"/api/v1/livros/{livro.id}/pausar",
            headers=HTMX_HEADERS,
        )
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "pausado" in resp.text.lower()

    async def test_testar_conexao_htmx_returns_badge(
        self, integration_client: AsyncClient
    ) -> None:
        from unittest.mock import AsyncMock, MagicMock, patch

        created = await integration_client.post(
            "/api/v1/configuracoes/apis",
            json={
                "tipo": "tts",
                "modo": "local",
                "url": "http://localhost:8001/health",
            },
            headers={"Accept": "application/json"},
        )
        config_id = created.json()["id"]

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
                headers=HTMX_HEADERS,
            )

        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Conectado" in resp.text
        assert "badge" in resp.text

    async def test_testar_conexao_falha_htmx_badge_vermelho(
        self, integration_client: AsyncClient
    ) -> None:
        created = await integration_client.post(
            "/api/v1/configuracoes/apis",
            json={
                "tipo": "llm",
                "modo": "cloud",
                "url": "http://invalid-host.local/ping",
            },
            headers={"Accept": "application/json"},
        )
        config_id = created.json()["id"]

        resp = await integration_client.post(
            f"/api/v1/configuracoes/apis/{config_id}/testar",
            headers=HTMX_HEADERS,
        )
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Falhou" in resp.text
