"""Capitulos API routes (v1) – chapter list and download."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_auth
from app.htmx import wants_html_partial
from app.models.capitulo import Capitulo
from app.models.livro import Livro
from app.models.usuario import Usuario
from app.schemas.capitulo import CapituloResumo, CapituloLista
from app.templating import templates


router = APIRouter(
    prefix="/livros/{livro_id}/capitulos",
    tags=["capitulos"],
    dependencies=[Depends(require_auth)],
)


async def _get_livro_or_404(db: AsyncSession, livro_id: int, usuario_id: int) -> Livro:
    result = await db.execute(
        select(Livro).where(
            Livro.id == livro_id,
            Livro.usuario_id == usuario_id,
            Livro.status != "excluido",
        )
    )
    livro = result.scalar_one_or_none()
    if livro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Livro não encontrado")
    return livro


@router.get("", response_model=CapituloLista)
async def listar_capitulos(
    request: Request,
    livro_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_auth)],
):
    """List all chapters for a book."""
    await _get_livro_or_404(db, livro_id, usuario.id)

    result = await db.execute(
        select(Capitulo)
        .where(Capitulo.livro_id == livro_id)
        .order_by(Capitulo.numero)
    )
    chapters = result.scalars().all()

    items = [CapituloResumo.model_validate(c) for c in chapters]

    if wants_html_partial(request):
        return templates.TemplateResponse(
            request=request,
            name="partials/capitulo_list.html",
            context={"request": request, "capitulos": items, "livro_id": livro_id},
        )

    return CapituloLista(items=items, total=len(items))


@router.get("/{capitulo_id}/download")
async def download_capitulo(
    livro_id: int,
    capitulo_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_auth)],
):
    """Download a chapter MP3 file."""
    await _get_livro_or_404(db, livro_id, usuario.id)

    result = await db.execute(
        select(Capitulo).where(Capitulo.id == capitulo_id, Capitulo.livro_id == livro_id)
    )
    cap = result.scalar_one_or_none()
    if cap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capítulo não encontrado")

    if not cap.caminho_audio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Áudio do capítulo não disponível")

    from pathlib import Path
    path = Path(cap.caminho_audio)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado no disco")

    return FileResponse(
        path=str(path),
        media_type="audio/mpeg",
        filename=path.name,
    )
