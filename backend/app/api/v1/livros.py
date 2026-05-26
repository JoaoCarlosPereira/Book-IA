"""Livros API routes (v1) — upload, fila, progresso, download."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_auth
from app.htmx import wants_html_partial
from app.models.usuario import Usuario
from app.render_livro import (
    render_livro_card,
    render_livro_list,
    render_progresso,
    render_upload_success,
)
from app.schemas.livro import (
    LivroDetalheResponse,
    LivroListResponse,
    LivroPrioridadeResponse,
    LivroProgresso,
    LivroReordenarRequest,
    LivroStatusResponse,
    LivroUploadResponse,
)
from app.services.livro_service import LivroService

router = APIRouter(
    prefix="/livros",
    tags=["livros"],
    dependencies=[Depends(require_auth)],
)


def _service(db: AsyncSession) -> LivroService:
    return LivroService(db)


@router.post("/upload", response_model=LivroUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_livro(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_auth)],
    arquivo: UploadFile = File(...),
    nivel_producao: str = Form(default="basico"),
) -> LivroUploadResponse | Response:
    """Upload PDF/EPUB/TXT and enqueue processing."""
    result = await _service(db).upload(usuario, arquivo, nivel_producao=nivel_producao)
    if wants_html_partial(request):
        return render_upload_success(request, result.id, result.status)
    return result


@router.get("", response_model=LivroListResponse)
async def listar_livros(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_auth)],
    status: str | None = Query(default=None, alias="status"),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, ge=1, le=100),
) -> LivroListResponse | Response:
    """List books for the current user with optional status filter."""
    data = await _service(db).listar(
        usuario.id,
        status_filter=status,
        pagina=pagina,
        por_pagina=por_pagina,
    )
    if wants_html_partial(request):
        return render_livro_list(request, data.items)
    return data


@router.get("/{livro_id}", response_model=LivroDetalheResponse)
async def obter_livro(
    livro_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_auth)],
) -> LivroDetalheResponse:
    """Book details including characters and task progress."""
    return await _service(db).obter_detalhe(livro_id, usuario.id)


@router.get("/{livro_id}/progresso", response_model=LivroProgresso)
async def obter_progresso(
    request: Request,
    livro_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_auth)],
) -> LivroProgresso | Response:
    """Current processing progress."""
    progresso = await _service(db).obter_progresso(livro_id, usuario.id)
    if wants_html_partial(request):
        return render_progresso(request, progresso)
    return progresso


async def _livro_card_after_action(
    request: Request,
    db: AsyncSession,
    livro_id: int,
    user_id: int,
) -> Response:
    """Reload book list item and render card partial for HTMX swap."""
    data = await _service(db).listar(user_id, pagina=1, por_pagina=100)
    livro = next((item for item in data.items if item.id == livro_id), None)
    if livro is None:
        detalhe = await _service(db).obter_detalhe(livro_id, user_id)
        livro = detalhe
    return render_livro_card(request, livro)  # type: ignore[arg-type]


@router.post("/{livro_id}/pausar", response_model=LivroStatusResponse)
async def pausar_livro(
    request: Request,
    livro_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_auth)],
) -> LivroStatusResponse | Response:
    """Pause book processing."""
    result = await _service(db).pausar(livro_id, usuario.id)
    if wants_html_partial(request):
        return await _livro_card_after_action(request, db, livro_id, usuario.id)
    return result


@router.post("/{livro_id}/retomar", response_model=LivroStatusResponse)
async def retomar_livro(
    request: Request,
    livro_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_auth)],
) -> LivroStatusResponse | Response:
    """Resume paused book processing."""
    result = await _service(db).retomar(livro_id, usuario.id)
    if wants_html_partial(request):
        return await _livro_card_after_action(request, db, livro_id, usuario.id)
    return result


@router.post("/{livro_id}/cancelar", response_model=LivroStatusResponse)
async def cancelar_livro(
    request: Request,
    livro_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_auth)],
) -> LivroStatusResponse | Response:
    """Cancel book processing."""
    result = await _service(db).cancelar(livro_id, usuario.id)
    if wants_html_partial(request):
        return await _livro_card_after_action(request, db, livro_id, usuario.id)
    return result


@router.post("/{livro_id}/reordenar", response_model=LivroPrioridadeResponse)
async def reordenar_livro(
    request: Request,
    livro_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_auth)],
) -> LivroPrioridadeResponse | Response:
    """Update queue priority for the book task."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = LivroReordenarRequest.model_validate(await request.json())
        prio = payload.prioridade
    else:
        form = await request.form()
        raw = form.get("prioridade")
        if raw is None:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="prioridade é obrigatória",
            )
        prio = int(raw)
    result = await _service(db).reordenar(livro_id, usuario.id, prio)
    if wants_html_partial(request):
        return await _livro_card_after_action(request, db, livro_id, usuario.id)
    return result


@router.get("/{livro_id}/download")
async def download_audiobook(
    livro_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_auth)],
) -> FileResponse:
    """Stream MP3 audiobook when processing is complete."""
    path = await _service(db).audio_path_for_download(livro_id, usuario.id)
    return FileResponse(
        path=path,
        media_type="audio/mpeg",
        filename=path.name,
    )


@router.delete(
    "/{livro_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def excluir_livro(
    livro_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_auth)],
) -> Response:
    """Soft-delete book and remove related files."""
    await _service(db).excluir(livro_id, usuario.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
