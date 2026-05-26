"""Tarefas / Book Task API routes and health checks."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_auth
from app.models.book_task import BookTask
from app.models.usuario import Usuario
from app.schemas.tarefas import ReorderRequest, TaskStatusResponse
from app.services import celery_health
from celery_worker import celery_app

router = APIRouter(prefix="/tarefas", tags=["tarefas"])
health_router = APIRouter(tags=["Monitoring"])


async def _get_task_or_404(task_id: int, db: AsyncSession) -> BookTask:
    result = await db.execute(select(BookTask).where(BookTask.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada")
    return task


@health_router.get("/health/redis")
async def health_redis():
    """Verify Redis broker connectivity."""
    payload = celery_health.check_redis()
    code = status.HTTP_200_OK if payload.get("redis") == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content=payload)


@health_router.get("/health/celery")
async def health_celery():
    """Verify at least one Celery worker is responding."""
    payload = celery_health.check_celery(celery_app)
    code = status.HTTP_200_OK if payload.get("celery") == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content=payload)


@router.post("/{task_id}/pausar", response_model=TaskStatusResponse)
async def pausar_tarefa(
    task_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[Usuario, Depends(require_auth)],
) -> TaskStatusResponse:
    """Pause a book processing task (stub — Celery revoke in task_10/11)."""
    task = await _get_task_or_404(task_id, db)
    if task.status not in ("pendente", "processando", "em_analise", "em_producao"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Não é possível pausar tarefa com status '{task.status}'",
        )
    task.status = "pausado"
    await db.flush()
    return TaskStatusResponse(
        task_id=task.id,
        livro_id=task.livro_id,
        status=task.status,
        prioridade=task.prioridade,
        progresso=task.progresso,
    )


@router.post("/{task_id}/retomar", response_model=TaskStatusResponse)
async def retomar_tarefa(
    task_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[Usuario, Depends(require_auth)],
) -> TaskStatusResponse:
    """Resume a paused book processing task."""
    task = await _get_task_or_404(task_id, db)
    if task.status != "pausado":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Não é possível retomar tarefa com status '{task.status}'",
        )
    task.status = "processando"
    await db.flush()
    return TaskStatusResponse(
        task_id=task.id,
        livro_id=task.livro_id,
        status=task.status,
        prioridade=task.prioridade,
        progresso=task.progresso,
    )


@router.post("/{task_id}/cancelar", response_model=TaskStatusResponse)
async def cancelar_tarefa(
    task_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[Usuario, Depends(require_auth)],
) -> TaskStatusResponse:
    """Cancel a pending or in-progress book task."""
    task = await _get_task_or_404(task_id, db)
    if task.status in ("concluido", "cancelado", "falhou"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Não é possível cancelar tarefa com status '{task.status}'",
        )
    task.status = "cancelado"
    await db.flush()
    return TaskStatusResponse(
        task_id=task.id,
        livro_id=task.livro_id,
        status=task.status,
        prioridade=task.prioridade,
        progresso=task.progresso,
    )


@router.post("/reordenar")
async def reordenar_fila(
    body: ReorderRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[Usuario, Depends(require_auth)],
) -> dict[str, int]:
    """Update priorities for multiple tasks in the queue."""
    updated = 0
    for item in body.items:
        result = await db.execute(select(BookTask).where(BookTask.id == item.task_id))
        task = result.scalar_one_or_none()
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tarefa {item.task_id} não encontrada",
            )
        task.prioridade = item.prioridade
        updated += 1
    await db.flush()
    return {"updated": updated}
