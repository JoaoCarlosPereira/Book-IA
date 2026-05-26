"""Celery application and task definitions."""

from __future__ import annotations

import logging
import signal
import tempfile
from pathlib import Path

from celery import Celery
from celery.signals import worker_shutdown

from app.celery_tasks.process_book import mark_book_failed, run_process_book
from app.config import settings
from app.db import SessionLocal
from app.models.book_task import BookTask

logger = logging.getLogger(__name__)

_temp_dirs: set[Path] = set()

celery_app = Celery(
    "bookia",
    broker=settings.celery_broker_url,
    backend=settings.celery_backend_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_routes={
        "celery_worker.process_book_task": {"queue": "bookia"},
    },
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=1,
)


def register_temp_dir(path: Path) -> None:
    """Track a temp directory for SIGTERM cleanup."""
    _temp_dirs.add(path)


def cleanup_temp_files() -> None:
    """Remove tracked temporary directories."""
    import shutil

    for path in list(_temp_dirs):
        try:
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
                logger.info("Removido diretório temporário: %s", path)
        except OSError as exc:
            logger.warning("Falha ao remover %s: %s", path, exc)
        finally:
            _temp_dirs.discard(path)


def _handle_sigterm(signum: int, frame: object | None) -> None:
    logger.info("SIGTERM recebido (signal=%s), limpando arquivos temporários", signum)
    cleanup_temp_files()


signal.signal(signal.SIGTERM, _handle_sigterm)


@worker_shutdown.connect
def _on_worker_shutdown(**_kwargs: object) -> None:
    cleanup_temp_files()


def _update_book_task(
    livro_id: int,
    *,
    status: str,
    progresso: int | None = None,
    etapa_atual: str | None = None,
    erro: str | None = None,
) -> None:
    """Update book_task row for a livro (sync session for Celery worker)."""
    db = SessionLocal()
    try:
        task = db.query(BookTask).filter(BookTask.livro_id == livro_id).first()
        if task is None:
            logger.warning("book_task não encontrada para livro_id=%s", livro_id)
            return
        task.status = status
        if progresso is not None:
            task.progresso = progresso
        if etapa_atual is not None:
            task.etapa_atual = etapa_atual
        if erro is not None:
            task.erro = erro
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(
    name="celery_worker.process_book_task",
    bind=True,
    max_retries=settings.celery_max_retries,
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
)
def process_book_task(self, livro_id: int) -> str:
    """Run the full book processing pipeline (PDF → IA → TTS → MusicGen → merge)."""
    work_dir = Path(tempfile.mkdtemp(prefix=f"bookia_{livro_id}_"))
    register_temp_dir(work_dir)

    logger.info("process_book_task iniciado livro_id=%s", livro_id)
    try:
        result = run_process_book(livro_id, work_dir)
        logger.info("process_book_task concluído livro_id=%s", livro_id)
        return result
    except Exception as exc:
        logger.exception("process_book_task falhou livro_id=%s", livro_id)
        if self.request.retries >= self.max_retries:
            mark_book_failed(livro_id, str(exc))
            raise
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc
    finally:
        if work_dir.exists():
            import shutil

            shutil.rmtree(work_dir, ignore_errors=True)
        _temp_dirs.discard(work_dir)
