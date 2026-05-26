"""Integration tests: upload → progress → download (Celery mocked by default)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.book_task import BookTask
from app.models.livro import Livro
from tests.test_integration.conftest import (
    epub_upload,
    pdf_upload,
    txt_upload,
    upload_file,
)


@pytest.mark.asyncio
class TestUploadPipelineIntegration:
    async def test_upload_pdf_enqueues_celery_task(
        self,
        integration_client: AsyncClient,
        mock_celery_delay: MagicMock,
        db_session,
    ) -> None:
        name, data, ctype = pdf_upload()
        response = await upload_file(integration_client, name, data, ctype)
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "pendente"
        livro_id = body["id"]

        task = (
            await db_session.execute(
                select(BookTask).where(BookTask.livro_id == livro_id)
            )
        ).scalar_one()
        assert task.celery_task_id == "celery-integration-task-id"
        mock_celery_delay.assert_called_once_with(livro_id)

    async def test_upload_epub_creates_livro(
        self, integration_client: AsyncClient, db_session
    ) -> None:
        name, data, ctype = epub_upload()
        response = await upload_file(integration_client, name, data, ctype)
        assert response.status_code == 201
        livro = (
            await db_session.execute(
                select(Livro).where(Livro.id == response.json()["id"])
            )
        ).scalar_one()
        assert livro.tipo_documento == "epub"

    async def test_upload_txt_creates_livro(
        self, integration_client: AsyncClient, db_session
    ) -> None:
        name, data, ctype = txt_upload()
        response = await upload_file(integration_client, name, data, ctype)
        assert response.status_code == 201
        livro = (
            await db_session.execute(
                select(Livro).where(Livro.id == response.json()["id"])
            )
        ).scalar_one()
        assert livro.tipo_documento == "txt"

    async def test_progresso_reflects_task_state(
        self, integration_client: AsyncClient, db_session
    ) -> None:
        livro = Livro(
            titulo="Prog",
            nome_arquivo="p.pdf",
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
                progresso=67,
                etapa_atual="AUDIO_PRODUCTION",
            )
        )
        await db_session.commit()

        resp = await integration_client.get(
            f"/api/v1/livros/{livro.id}/progresso",
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json() == {
            "progresso": 67,
            "etapa": "AUDIO_PRODUCTION",
            "status": "processando",
        }

    async def test_download_mp3_after_completion(
        self,
        integration_client: AsyncClient,
        db_session,
        livros_storage: Path,
    ) -> None:
        audio_dir = livros_storage / "audio" / "1"
        audio_dir.mkdir(parents=True)
        mp3_path = audio_dir / "audiobook.mp3"
        mp3_path.write_bytes(b"ID3integration")

        livro = Livro(
            titulo="Done",
            nome_arquivo="d.pdf",
            tipo_documento="pdf",
            nivel_producao="basico",
            status="concluido",
            progresso=100,
            caminho_audio=str(mp3_path),
            usuario_id=1,
        )
        db_session.add(livro)
        await db_session.commit()

        resp = await integration_client.get(f"/api/v1/livros/{livro.id}/download")
        assert resp.status_code == 200
        assert resp.content == b"ID3integration"
        assert "audio" in resp.headers.get("content-type", "")

    async def test_upload_to_progress_to_download_flow(
        self,
        integration_client: AsyncClient,
        db_session,
        livros_storage: Path,
        mock_celery_delay: MagicMock,
    ) -> None:
        """Upload → mocked Celery enqueue → completed state → progress → download."""
        name, data, ctype = pdf_upload()
        upload_resp = await upload_file(integration_client, name, data, ctype)
        assert upload_resp.status_code == 201
        livro_id = upload_resp.json()["id"]
        mock_celery_delay.assert_called_once_with(livro_id)

        audio_dir = livros_storage / "audio" / str(livro_id)
        audio_dir.mkdir(parents=True)
        mp3_path = audio_dir / "audiobook.mp3"
        mp3_path.write_bytes(b"ID3flow")

        livro = (
            await db_session.execute(select(Livro).where(Livro.id == livro_id))
        ).scalar_one()
        livro.status = "concluido"
        livro.progresso = 100
        livro.caminho_audio = str(mp3_path)
        task = (
            await db_session.execute(
                select(BookTask).where(BookTask.livro_id == livro_id)
            )
        ).scalar_one()
        task.status = "concluido"
        task.progresso = 100
        task.etapa_atual = "UNIFICAR"
        await db_session.commit()

        progress = await integration_client.get(
            f"/api/v1/livros/{livro_id}/progresso",
            headers={"Accept": "application/json"},
        )
        assert progress.status_code == 200
        assert progress.json()["progresso"] == 100
        assert progress.json()["status"] == "concluido"

        download = await integration_client.get(f"/api/v1/livros/{livro_id}/download")
        assert download.status_code == 200
        assert download.content == b"ID3flow"
