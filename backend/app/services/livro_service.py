"""Business logic for livros upload, queue, and lifecycle."""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models.book_task import BookTask
from app.models.livro import Livro
from app.models.personagem import Personagem
from app.models.capitulo import Capitulo
from app.models.usuario import Usuario
from app.schemas.livro import (
    EXTENSION_TO_DOC_TYPE,
    LivroDetalheResponse,
    LivroListItem,
    LivroListResponse,
    LivroPrioridadeResponse,
    LivroProgresso,
    LivroStatusResponse,
    LivroUploadResponse,
    PersonagemResumo,
    VALID_EXTENSIONS,
)
logger = logging.getLogger(__name__)


def _enqueue_book_task(livro_id: int):
    """Dispatch Celery processing (lazy import for testability)."""
    from celery_worker import process_book_task

    return process_book_task.delay(livro_id)


def _revoke_celery_by_id(celery_task_id: str, *, terminate: bool = False) -> None:
    from celery_worker import celery_app

    celery_app.control.revoke(
        celery_task_id,
        terminate=terminate,
        signal="SIGTERM",
    )

PAUSABLE_STATUSES = frozenset({"pendente", "processando", "em_analise", "em_producao"})
CANCELLABLE_STATUSES = PAUSABLE_STATUSES | frozenset({"pausado"})
ACTIVE_STATUSES = PAUSABLE_STATUSES | frozenset({"pausado"})


def _sanitize_filename(name: str) -> str:
    base = Path(name).name
    safe = re.sub(r"[^\w.\-]", "_", base, flags=re.UNICODE)
    return safe or "upload"


def _ensure_storage_dirs() -> None:
    Path(settings.pdfs_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.audio_dir).mkdir(parents=True, exist_ok=True)


class LivroService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def _get_livro_or_404(self, livro_id: int, usuario_id: int) -> Livro:
        result = await self._db.execute(
            select(Livro).where(
                Livro.id == livro_id,
                Livro.usuario_id == usuario_id,
                Livro.status != "excluido",
            )
        )
        livro = result.scalar_one_or_none()
        if livro is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Livro não encontrado",
            )
        return livro

    async def _get_chapters(self, livro_id: int) -> list:
        result = await self._db.execute(
            select(Capitulo).where(Capitulo.livro_id == livro_id).order_by(Capitulo.numero)
        )
        return result.scalars().all()

    async def _get_book_task(self, livro_id: int) -> BookTask | None:
        result = await self._db.execute(
            select(BookTask).where(BookTask.livro_id == livro_id)
        )
        return result.scalar_one_or_none()

    async def upload(
        self,
        usuario: Usuario,
        file: UploadFile,
        nivel_producao: str = "basico",
    ) -> LivroUploadResponse:
        if nivel_producao not in ("basico", "avancado", "profissional"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="nivel_producao deve ser basico, avancado ou profissional",
            )

        filename = file.filename or ""
        ext = Path(filename).suffix.lower()
        if ext not in VALID_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de arquivo não permitido. Use: {', '.join(sorted(VALID_EXTENSIONS))}",
            )

        content = await file.read()
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Arquivo excede o limite de {settings.max_upload_size_mb}MB",
            )
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo vazio",
            )

        _ensure_storage_dirs()
        safe_name = _sanitize_filename(filename)
        titulo = Path(safe_name).stem[:500]
        doc_type = EXTENSION_TO_DOC_TYPE[ext]

        livro = Livro(
            titulo=titulo,
            nome_arquivo=safe_name,
            tipo_documento=doc_type,
            nivel_producao=nivel_producao,
            status="pendente",
            progresso=0,
            usuario_id=usuario.id,
        )
        self._db.add(livro)
        await self._db.flush()

        livro_dir = Path(settings.pdfs_dir) / str(livro.id)
        livro_dir.mkdir(parents=True, exist_ok=True)
        dest_path = livro_dir / safe_name
        dest_path.write_bytes(content)
        livro.caminho_pdf = str(dest_path)

        book_task = BookTask(
            livro_id=livro.id,
            status="pendente",
            prioridade=5,
            progresso=0,
            etapa_atual="aguardando",
        )
        self._db.add(book_task)
        await self._db.flush()

        async_result = _enqueue_book_task(livro.id)
        book_task.celery_task_id = async_result.id
        logger.info(
            "Upload livro_id=%s celery_task_id=%s",
            livro.id,
            async_result.id,
        )

        return LivroUploadResponse(id=livro.id, status=livro.status)

    async def listar(
        self,
        usuario_id: int,
        *,
        status_filter: str | None = None,
        pagina: int = 1,
        por_pagina: int = 20,
    ) -> LivroListResponse:
        if pagina < 1:
            pagina = 1
        if por_pagina < 1:
            por_pagina = 20
        if por_pagina > 100:
            por_pagina = 100

        base = select(Livro).where(Livro.usuario_id == usuario_id)
        if status_filter:
            base = base.where(Livro.status == status_filter)
        else:
            base = base.where(Livro.status != "excluido")

        count_filters = [Livro.usuario_id == usuario_id]
        if status_filter:
            count_filters.append(Livro.status == status_filter)
        else:
            count_filters.append(Livro.status != "excluido")
        count_stmt = select(func.count()).select_from(Livro).where(*count_filters)
        total_result = await self._db.execute(count_stmt)
        total = total_result.scalar_one()

        offset = (pagina - 1) * por_pagina
        stmt = (
            base.order_by(Livro.criado_em.desc())
            .offset(offset)
            .limit(por_pagina)
        )
        result = await self._db.execute(stmt)
        rows = result.scalars().all()

        return LivroListResponse(
            items=[LivroListItem.model_validate(r) for r in rows],
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
        )

    async def obter_detalhe(
        self, livro_id: int, usuario_id: int
    ) -> LivroDetalheResponse:
        result = await self._db.execute(
            select(Livro).where(
                Livro.id == livro_id,
                Livro.usuario_id == usuario_id,
                Livro.status != "excluido",
            )
        )
        livro = result.scalar_one_or_none()
        if livro is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Livro não encontrado",
            )

        pers_result = await self._db.execute(
            select(Personagem).where(Personagem.livro_id == livro_id)
        )
        personagens = pers_result.scalars().all()
        chapters = await self._get_chapters(livro_id)
        task = await self._get_book_task(livro_id)

        etapa = task.etapa_atual if task else None
        task_status = task.status if task else None
        progresso = task.progresso if task else livro.progresso

        return LivroDetalheResponse(
            id=livro.id,
            titulo=livro.titulo,
            nome_arquivo=livro.nome_arquivo,
            tipo_documento=livro.tipo_documento,
            nivel_producao=livro.nivel_producao,
            status=livro.status,
            progresso=progresso,
            etapa=etapa,
            task_status=task_status,
            prioridade=task.prioridade if task else None,
            erro=task.erro if task else None,
            criado_em=livro.criado_em,
            atualizado_em=livro.atualizado_em,
            personagens=[PersonagemResumo.model_validate(p) for p in personagens],
            capitulos=[{"id": c.id, "numero": c.numero, "titulo": c.titulo, "pagina_inicio": c.pagina_inicio, "pagina_fim": c.pagina_fim, "caminho_audio": c.caminho_audio} for c in chapters],
        )

    async def obter_progresso(
        self, livro_id: int, usuario_id: int
    ) -> LivroProgresso:
        livro = await self._get_livro_or_404(livro_id, usuario_id)
        task = await self._get_book_task(livro_id)
        if task is None:
            return LivroProgresso(
                progresso=livro.progresso,
                etapa="desconhecida",
                status=livro.status,
            )
        return LivroProgresso(
            progresso=task.progresso,
            etapa=task.etapa_atual or "",
            status=task.status,
        )

    def _revoke_celery_task(self, task: BookTask, *, terminate: bool = False) -> None:
        if not task.celery_task_id:
            return
        try:
            _revoke_celery_by_id(task.celery_task_id, terminate=terminate)
            logger.info("Celery task revogada: %s", task.celery_task_id)
        except Exception as exc:
            logger.warning("Falha ao revogar Celery task %s: %s", task.celery_task_id, exc)

    async def pausar(self, livro_id: int, usuario_id: int) -> LivroStatusResponse:
        livro = await self._get_livro_or_404(livro_id, usuario_id)
        task = await self._get_book_task(livro_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarefa de processamento não encontrada",
            )
        if task.status not in PAUSABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Não é possível pausar com status '{task.status}'",
            )
        task.status = "pausado"
        livro.status = "pausado"
        self._revoke_celery_task(task, terminate=False)
        await self._db.flush()
        return LivroStatusResponse(status=task.status)

    async def retomar(self, livro_id: int, usuario_id: int) -> LivroStatusResponse:
        livro = await self._get_livro_or_404(livro_id, usuario_id)
        task = await self._get_book_task(livro_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarefa de processamento não encontrada",
            )
        if task.status != "pausado":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Não é possível retomar com status '{task.status}'",
            )
        task.status = "processando"
        livro.status = "processando"
        async_result = _enqueue_book_task(livro_id)
        task.celery_task_id = async_result.id
        await self._db.flush()
        return LivroStatusResponse(status=task.status)

    async def cancelar(self, livro_id: int, usuario_id: int) -> LivroStatusResponse:
        livro = await self._get_livro_or_404(livro_id, usuario_id)
        task = await self._get_book_task(livro_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarefa de processamento não encontrada",
            )
        if task.status in ("concluido", "cancelado", "falhou", "excluido"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Não é possível cancelar com status '{task.status}'",
            )
        task.status = "cancelado"
        livro.status = "cancelado"
        self._revoke_celery_task(task, terminate=True)
        await self._db.flush()
        return LivroStatusResponse(status=task.status)

    async def reordenar(
        self, livro_id: int, usuario_id: int, prioridade: int
    ) -> LivroPrioridadeResponse:
        await self._get_livro_or_404(livro_id, usuario_id)
        task = await self._get_book_task(livro_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarefa de processamento não encontrada",
            )
        task.prioridade = prioridade
        await self._db.flush()
        return LivroPrioridadeResponse(prioridade=task.prioridade)

    async def audio_path_for_download(
        self, livro_id: int, usuario_id: int
    ) -> Path:
        livro = await self._get_livro_or_404(livro_id, usuario_id)
        return self.resolve_audio_path(livro)

    def resolve_audio_path(self, livro: Livro) -> Path:
        if livro.status != "concluido":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Audiobook ainda não está disponível",
            )
        if not livro.caminho_audio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo de áudio não encontrado",
            )
        path = Path(livro.caminho_audio)
        if not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo de áudio não encontrado no disco",
            )
        return path

    async def excluir(self, livro_id: int, usuario_id: int) -> None:
        livro = await self._get_livro_or_404(livro_id, usuario_id)
        task = await self._get_book_task(livro_id)
        if task and task.status in ACTIVE_STATUSES:
            self._revoke_celery_task(task, terminate=True)
            task.status = "cancelado"

        livro.status = "excluido"
        self._cleanup_files(livro)
        if task:
            await self._db.flush()

    def _cleanup_files(self, livro: Livro) -> None:
        paths: list[Path] = []
        if livro.caminho_pdf:
            paths.append(Path(livro.caminho_pdf))
        if livro.caminho_audio:
            paths.append(Path(livro.caminho_audio))

        for path in paths:
            try:
                if path.is_file():
                    path.unlink()
            except OSError as exc:
                logger.warning("Falha ao remover arquivo %s: %s", path, exc)

        livro_dir = Path(settings.pdfs_dir) / str(livro.id)
        if livro_dir.is_dir():
            shutil.rmtree(livro_dir, ignore_errors=True)

        audio_book_dir = Path(settings.audio_dir) / str(livro.id)
        if audio_book_dir.is_dir():
            shutil.rmtree(audio_book_dir, ignore_errors=True)
