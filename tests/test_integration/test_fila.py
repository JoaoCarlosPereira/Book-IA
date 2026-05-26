"""Integration tests: queue with multiple books — pause, resume, cancel, reorder."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.book_task import BookTask
from app.models.livro import Livro
from tests.test_integration.conftest import pdf_upload, upload_file


@pytest.mark.asyncio
class TestFilaIntegration:
    async def _upload_three(
        self, client: AsyncClient
    ) -> list[int]:
        ids: list[int] = []
        for i in range(3):
            name, data, ctype = pdf_upload(f"livro_{i}.pdf", f"%PDF-{i}".encode())
            resp = await upload_file(client, name, data, ctype)
            assert resp.status_code == 201
            ids.append(resp.json()["id"])
        return ids

    async def test_three_books_in_queue_all_pending(
        self,
        integration_client: AsyncClient,
        mock_celery_delay,
        db_session,
    ) -> None:
        ids = await self._upload_three(integration_client)
        assert mock_celery_delay.call_count == 3

        resp = await integration_client.get(
            "/api/v1/livros",
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 3
        returned_ids = {item["id"] for item in resp.json()["items"]}
        assert returned_ids == set(ids)

        tasks = (await db_session.execute(select(BookTask))).scalars().all()
        assert len(tasks) == 3
        assert all(t.status == "pendente" for t in tasks)

    async def test_pausar_atualiza_status(
        self, integration_client: AsyncClient, db_session
    ) -> None:
        livro_id = (await self._upload_three(integration_client))[0]
        livro = await db_session.get(Livro, livro_id)
        livro.status = "processando"
        task = (
            await db_session.execute(
                select(BookTask).where(BookTask.livro_id == livro_id)
            )
        ).scalar_one()
        task.status = "processando"
        await db_session.commit()

        resp = await integration_client.post(
            f"/api/v1/livros/{livro_id}/pausar",
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pausado"

    async def test_retomar_reenfileira_celery(
        self,
        integration_client: AsyncClient,
        db_session,
        mock_celery_delay,
    ) -> None:
        livro_id = (await self._upload_three(integration_client))[1]
        mock_celery_delay.reset_mock()

        livro = await db_session.get(Livro, livro_id)
        livro.status = "pausado"
        task = (
            await db_session.execute(
                select(BookTask).where(BookTask.livro_id == livro_id)
            )
        ).scalar_one()
        task.status = "pausado"
        await db_session.commit()

        resp = await integration_client.post(
            f"/api/v1/livros/{livro_id}/retomar",
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "processando"
        mock_celery_delay.assert_called_once_with(livro_id)

    async def test_cancelar_cancela_processamento(
        self, integration_client: AsyncClient, db_session
    ) -> None:
        livro_id = (await self._upload_three(integration_client))[2]
        livro = await db_session.get(Livro, livro_id)
        livro.status = "processando"
        task = (
            await db_session.execute(
                select(BookTask).where(BookTask.livro_id == livro_id)
            )
        ).scalar_one()
        task.status = "processando"
        await db_session.commit()

        resp = await integration_client.post(
            f"/api/v1/livros/{livro_id}/cancelar",
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelado"

    async def test_reordenar_muda_prioridade(
        self, integration_client: AsyncClient, db_session
    ) -> None:
        ids = await self._upload_three(integration_client)
        livro_id = ids[0]

        resp = await integration_client.post(
            f"/api/v1/livros/{livro_id}/reordenar",
            json={"prioridade": 1},
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["prioridade"] == 1

        task = (
            await db_session.execute(
                select(BookTask).where(BookTask.livro_id == livro_id)
            )
        ).scalar_one()
        assert task.prioridade == 1
