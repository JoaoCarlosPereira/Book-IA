"""Fixtures shared by integration tests (auth, upload, fila, HTMX, Celery)."""

from __future__ import annotations


def pytest_configure(config) -> None:
    """Integration runs focus on flows; do not fail on service coverage thresholds."""
    if hasattr(config.option, "cov_fail_under"):
        config.option.cov_fail_under = 0

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.config import settings


@pytest.fixture(autouse=True)
def livros_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated upload/audio directories for each integration test."""
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
    """Mock Celery enqueue/revoke for deterministic integration tests."""
    result = MagicMock()
    result.id = "celery-integration-task-id"
    with (
        patch(
            "app.services.livro_service._enqueue_book_task",
            return_value=result,
        ) as mock_enqueue,
        patch("app.services.livro_service._revoke_celery_by_id") as mock_revoke,
    ):
        yield mock_enqueue


def pdf_upload(filename: str = "livro.pdf", content: bytes = b"%PDF-1.4 minimal") -> tuple[str, bytes, str]:
    return (filename, content, "application/pdf")


def epub_upload() -> tuple[str, bytes, str]:
    return ("livro.epub", b"PK\x03\x04 epub", "application/epub+zip")


def txt_upload() -> tuple[str, bytes, str]:
    return ("capitulo.txt", b"Capitulo um.\n", "text/plain")


async def upload_file(
    client: AsyncClient,
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream",
    nivel: str = "basico",
    *,
    htmx: bool = False,
) -> object:
    """POST /api/v1/livros/upload helper."""
    headers: dict[str, str] = {}
    if htmx:
        from tests.conftest import HTMX_HEADERS

        headers.update(HTMX_HEADERS)
    else:
        headers["Accept"] = "application/json"

    return await client.post(
        "/api/v1/livros/upload",
        files={"arquivo": (filename, BytesIO(content), content_type)},
        data={"nivel_producao": nivel},
        headers=headers,
    )
