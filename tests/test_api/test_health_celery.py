"""Health endpoints for Redis and Celery."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

import app.api.v1.tarefas as tarefas_module


@pytest.mark.asyncio
class TestHealthRedis:
    async def test_health_redis_ok(self, client: AsyncClient) -> None:
        with patch.object(tarefas_module.celery_health, "check_redis", return_value={"redis": "ok"}):
            response = await client.get("/health/redis")

        assert response.status_code == 200
        assert response.json() == {"redis": "ok"}

    async def test_health_redis_error(self, client: AsyncClient) -> None:
        with patch.object(
            tarefas_module.celery_health,
            "check_redis",
            return_value={"redis": "error", "detail": "redis down"},
        ):
            response = await client.get("/health/redis")

        assert response.status_code == 503
        data = response.json()
        assert data["redis"] == "error"
        assert "detail" in data


@pytest.mark.asyncio
class TestHealthCelery:
    async def test_health_celery_ok(self, client: AsyncClient) -> None:
        with patch.object(
            tarefas_module.celery_health,
            "check_celery",
            return_value={"celery": "ok", "worker_count": 1},
        ):
            response = await client.get("/health/celery")

        assert response.status_code == 200
        assert response.json() == {"celery": "ok", "worker_count": 1}

    async def test_health_celery_no_workers(self, client: AsyncClient) -> None:
        with patch.object(
            tarefas_module.celery_health,
            "check_celery",
            return_value={
                "celery": "error",
                "detail": "Nenhum worker Celery respondeu",
                "worker_count": 0,
            },
        ):
            response = await client.get("/health/celery")

        assert response.status_code == 503
        data = response.json()
        assert data["celery"] == "error"
        assert data["worker_count"] == 0


@pytest.mark.asyncio
class TestTarefasQueueControl:
    async def _create_task(self, db_session, authenticated_client: AsyncClient) -> int:
        from sqlalchemy import select

        from app.models.book_task import BookTask
        from app.models.livro import Livro
        from app.models.usuario import Usuario

        result = await db_session.execute(select(Usuario).limit(1))
        user = result.scalar_one()
        livro = Livro(
            titulo="Fila",
            nome_arquivo="f.pdf",
            tipo_documento="pdf",
            nivel_producao="completo",
            status="pendente",
            usuario_id=user.id,
        )
        db_session.add(livro)
        await db_session.flush()

        task = BookTask(livro_id=livro.id, status="processando", prioridade=5, progresso=10)
        db_session.add(task)
        await db_session.commit()
        return task.id

    async def test_pausar_atualiza_status(
        self, db_session, authenticated_client: AsyncClient
    ) -> None:
        task_id = await self._create_task(db_session, authenticated_client)
        response = await authenticated_client.post(f"/api/v1/tarefas/{task_id}/pausar")
        assert response.status_code == 200
        assert response.json()["status"] == "pausado"

    async def test_retomar_atualiza_status(
        self, db_session, authenticated_client: AsyncClient
    ) -> None:
        task_id = await self._create_task(db_session, authenticated_client)
        await authenticated_client.post(f"/api/v1/tarefas/{task_id}/pausar")
        response = await authenticated_client.post(f"/api/v1/tarefas/{task_id}/retomar")
        assert response.status_code == 200
        assert response.json()["status"] == "processando"

    async def test_cancelar_atualiza_status(
        self, db_session, authenticated_client: AsyncClient
    ) -> None:
        task_id = await self._create_task(db_session, authenticated_client)
        response = await authenticated_client.post(f"/api/v1/tarefas/{task_id}/cancelar")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelado"

    async def test_reordenar_prioridades(
        self, db_session, authenticated_client: AsyncClient
    ) -> None:
        task_id = await self._create_task(db_session, authenticated_client)
        response = await authenticated_client.post(
            "/api/v1/tarefas/reordenar",
            json={"items": [{"task_id": task_id, "prioridade": 1}]},
        )
        assert response.status_code == 200
        assert response.json()["updated"] == 1
