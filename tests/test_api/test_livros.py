"""Tests for livros API — upload, queue, progress, download."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.config import settings
from app.models.book_task import BookTask
from app.models.livro import Livro


@pytest.fixture(autouse=True)
def livros_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated upload/audio directories for each test."""
    pdfs = tmp_path / "pdfs"
    audio = tmp_path / "audio"
    pdfs.mkdir()
    audio.mkdir()
    monkeypatch.setattr(settings, "pdfs_dir", str(pdfs))
    monkeypatch.setattr(settings, "audio_dir", str(audio))
    monkeypatch.setattr(settings, "max_upload_size_mb", 50)
    return tmp_path


@pytest.fixture(autouse=True)
def mock_celery_delay():
    """Mock Celery enqueue/revoke for all livros API tests."""
    result = MagicMock()
    result.id = "celery-task-test-id"
    with (
        patch(
            "app.services.livro_service._enqueue_book_task",
            return_value=result,
        ) as mock_enqueue,
        patch("app.services.livro_service._revoke_celery_by_id") as mock_revoke,
    ):
        yield mock_enqueue


def _pdf_bytes(content: bytes = b"%PDF-1.4 minimal") -> tuple[str, bytes, str]:
    return ("livro.pdf", content, "application/pdf")


def _epub_bytes() -> tuple[str, bytes, str]:
    return ("livro.epub", b"PK\x03\x04 epub", "application/epub+zip")


def _txt_bytes() -> tuple[str, bytes, str]:
    return ("capitulo.txt", b"Capitulo um.\n", "text/plain")


async def _upload(
    client: AsyncClient,
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream",
    nivel: str = "basico",
) -> object:
    return await client.post(
        "/api/v1/livros/upload",
        files={"arquivo": (filename, BytesIO(content), content_type)},
        data={"nivel_producao": nivel},
        headers={"Accept": "application/json"},
    )


@pytest.mark.asyncio
class TestLivrosUpload:
    async def test_upload_pdf_creates_livro_and_task(
        self,
        authenticated_client: AsyncClient,
        mock_celery_delay: MagicMock,
        db_session,
    ) -> None:
        name, data, ctype = _pdf_bytes()
        response = await _upload(authenticated_client, name, data, ctype)
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "pendente"
        livro_id = body["id"]

        livro = (
            await db_session.execute(select(Livro).where(Livro.id == livro_id))
        ).scalar_one()
        assert livro.tipo_documento == "pdf"
        assert Path(livro.caminho_pdf).is_file()

        task = (
            await db_session.execute(
                select(BookTask).where(BookTask.livro_id == livro_id)
            )
        ).scalar_one()
        assert task.status == "pendente"
        assert task.celery_task_id == "celery-task-test-id"
        mock_celery_delay.assert_called_once_with(livro_id)

    async def test_upload_epub(
        self, authenticated_client: AsyncClient, mock_celery_delay: MagicMock
    ) -> None:
        name, data, ctype = _epub_bytes()
        response = await _upload(authenticated_client, name, data, ctype)
        assert response.status_code == 201
        assert response.json()["status"] == "pendente"

    async def test_upload_txt(
        self, authenticated_client: AsyncClient, mock_celery_delay: MagicMock
    ) -> None:
        name, data, ctype = _txt_bytes()
        response = await _upload(authenticated_client, name, data, ctype)
        assert response.status_code == 201

    async def test_upload_invalid_extension(
        self, authenticated_client: AsyncClient, mock_celery_delay: MagicMock
    ) -> None:
        response = await _upload(
            authenticated_client, "virus.exe", b"MZ", "application/octet-stream"
        )
        assert response.status_code == 400
        mock_celery_delay.assert_not_called()

    async def test_upload_exceeds_size(
        self,
        authenticated_client: AsyncClient,
        mock_celery_delay: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(settings, "max_upload_size_mb", 1)
        big = b"x" * (2 * 1024 * 1024)
        response = await _upload(authenticated_client, "big.pdf", big)
        assert response.status_code == 400
        mock_celery_delay.assert_not_called()

    async def test_requires_auth(self, client: AsyncClient) -> None:
        name, data, ctype = _pdf_bytes()
        response = await _upload(client, name, data, ctype)
        assert response.status_code == 401


@pytest.mark.asyncio
class TestLivrosListAndDetail:
    async def _seed_livro(
        self, db_session, usuario_id: int = 1, status: str = "pendente"
    ) -> Livro:
        livro = Livro(
            titulo="Teste",
            nome_arquivo="t.pdf",
            tipo_documento="pdf",
            nivel_producao="basico",
            status=status,
            progresso=10,
            usuario_id=usuario_id,
        )
        db_session.add(livro)
        await db_session.flush()
        db_session.add(
            BookTask(
                livro_id=livro.id,
                status=status,
                prioridade=5,
                progresso=10,
                etapa_atual="extracao",
            )
        )
        await db_session.commit()
        return livro

    async def test_list_with_status_filter(
        self, authenticated_client: AsyncClient, db_session
    ) -> None:
        await self._seed_livro(db_session, status="pendente")
        await self._seed_livro(db_session, status="concluido")

        resp = await authenticated_client.get(
            "/api/v1/livros",
            params={"status": "pendente"},
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "pendente"

    async def test_get_detail(
        self, authenticated_client: AsyncClient, db_session
    ) -> None:
        livro = await self._seed_livro(db_session)
        resp = await authenticated_client.get(
            f"/api/v1/livros/{livro.id}",
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == livro.id
        assert data["task_status"] == "pendente"
        assert data["etapa"] == "extracao"


@pytest.mark.asyncio
class TestLivrosProgresso:
    async def test_progresso(
        self, authenticated_client: AsyncClient, db_session
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
                progresso=42,
                etapa_atual="tts",
            )
        )
        await db_session.commit()

        resp = await authenticated_client.get(
            f"/api/v1/livros/{livro.id}/progresso",
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json() == {
            "progresso": 42,
            "etapa": "tts",
            "status": "processando",
        }


@pytest.mark.asyncio
class TestLivrosControle:
    async def _livro_com_task(
        self, db_session, task_status: str = "processando"
    ) -> Livro:
        livro = Livro(
            titulo="Ctrl",
            nome_arquivo="c.pdf",
            tipo_documento="pdf",
            nivel_producao="basico",
            status=task_status,
            progresso=0,
            usuario_id=1,
        )
        db_session.add(livro)
        await db_session.flush()
        db_session.add(
            BookTask(
                livro_id=livro.id,
                status=task_status,
                prioridade=5,
                progresso=0,
                etapa_atual="ia",
                celery_task_id="task-123",
            )
        )
        await db_session.commit()
        return livro

    async def test_pausar(
        self, authenticated_client: AsyncClient, db_session
    ) -> None:
        livro = await self._livro_com_task(db_session, "processando")
        resp = await authenticated_client.post(
            f"/api/v1/livros/{livro.id}/pausar",
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pausado"

    async def test_retomar(
        self, authenticated_client: AsyncClient, db_session, mock_celery_delay
    ) -> None:
        livro = await self._livro_com_task(db_session, "pausado")
        resp = await authenticated_client.post(
            f"/api/v1/livros/{livro.id}/retomar",
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "processando"
        mock_celery_delay.assert_called_once_with(livro.id)

    async def test_cancelar(
        self, authenticated_client: AsyncClient, db_session
    ) -> None:
        livro = await self._livro_com_task(db_session, "processando")
        resp = await authenticated_client.post(
            f"/api/v1/livros/{livro.id}/cancelar",
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelado"

    async def test_reordenar(
        self, authenticated_client: AsyncClient, db_session
    ) -> None:
        livro = await self._livro_com_task(db_session)
        resp = await authenticated_client.post(
            f"/api/v1/livros/{livro.id}/reordenar",
            json={"prioridade": 1},
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["prioridade"] == 1


@pytest.mark.asyncio
class TestLivrosDownload:
    async def test_download_mp3_stream(
        self,
        authenticated_client: AsyncClient,
        db_session,
        livros_storage: Path,
    ) -> None:
        audio_dir = livros_storage / "audio" / "1"
        audio_dir.mkdir(parents=True)
        mp3_path = audio_dir / "audiobook.mp3"
        mp3_path.write_bytes(b"ID3fake")

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

        resp = await authenticated_client.get(
            f"/api/v1/livros/{livro.id}/download",
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.content == b"ID3fake"
        assert "audio" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
class TestLivrosDelete:
    async def test_delete_soft_and_cleanup(
        self,
        authenticated_client: AsyncClient,
        db_session,
        livros_storage: Path,
    ) -> None:
        pdf_dir = livros_storage / "pdfs" / "99"
        pdf_dir.mkdir(parents=True)
        pdf_file = pdf_dir / "doc.pdf"
        pdf_file.write_bytes(b"%PDF")

        livro = Livro(
            titulo="Del",
            nome_arquivo="doc.pdf",
            tipo_documento="pdf",
            nivel_producao="basico",
            status="pendente",
            progresso=0,
            caminho_pdf=str(pdf_file),
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
        livro_id = livro.id

        resp = await authenticated_client.delete(
            f"/api/v1/livros/{livro_id}",
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 204

        db_session.expire_all()
        row = (
            await db_session.execute(select(Livro).where(Livro.id == livro_id))
        ).scalar_one()
        assert row.status == "excluido"
        assert not pdf_file.exists()

        list_resp = await authenticated_client.get(
            "/api/v1/livros",
            headers={"Accept": "application/json"},
        )
        assert list_resp.json()["total"] == 0
