"""Revisao API routes (v1) — character review for Fase 2."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_auth
from app.htmx import wants_html_partial
from app.models.falas import Fala
from app.models.livro import Livro
from app.models.pagina import Pagina
from app.models.personagem import Personagem
from app.models.usuario import Usuario
from app.templating import templates

router = APIRouter(
    prefix="/livros/{livro_id}/revisao",
    tags=["revisao"],
    dependencies=[Depends(require_auth)],
)


class FalaResumo(BaseModel):
    id: int
    texto: str
    pagina_numero: int
    model_config = ConfigDict(from_attributes=True)


class PersonagemItem(BaseModel):
    id: int
    nome: str
    nome_original: str | None = None
    genero: str | None = None
    idade: str | None = None
    is_narrador: bool = False
    voz_id: int | None = None
    falas: list[FalaResumo] = []
    model_config = ConfigDict(from_attributes=True)


class PersonagemUpdateRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    genero: str = Field(description="masculino, feminino, neutro")
    idade: str = Field(description="crianca, adulto, idoso")
    voz_id: int | None = None


async def _obter_livro_livre(db: AsyncSession, livro_id: int, usuario_id: int) -> Livro:
    result = await db.execute(
        select(Livro).where(Livro.id == livro_id, Livro.usuario_id == usuario_id)
    )
    livro = result.scalar_one_or_none()
    if livro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro nao encontrado",
        )
    return livro


@router.get("")
async def listar_personagens(
    request: Request,
    livro_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_auth)],
):
    """List all characters with their dialogues for review."""
    await _obter_livro_livre(db, livro_id, usuario.id)

    personagens = (
        await db.execute(
            select(Personagem).where(Personagem.livro_id == livro_id)
        )
    ).scalars().all()

    result = []
    for p in personagens:
        rows = (
            await db.execute(
                select(Fala.id, Fala.texto, Pagina.numero)
                .join(Pagina, Fala.pagina_id == Pagina.id)
                .where(Fala.personagem_id == p.id)
                .order_by(Pagina.numero, Fala.id)
            )
        ).all()
        falas = [FalaResumo(id=r[0], texto=r[1], pagina_numero=r[2]) for r in rows]
        result.append(PersonagemItem(
            id=p.id, nome=p.nome, nome_original=p.nome_original,
            genero=p.genero, idade=p.idade,
            is_narrador=p.is_narrador, voz_id=p.voz_id, falas=falas,
        ))

    if wants_html_partial(request):
        return templates.TemplateResponse(
            request=request,
            name="partials/revisao_personagem_list.html",
            context={"request": request, "personagens": result},
        )
    return result


@router.put("/personagem/{personagem_id}")
async def atualizar_personagem(
    request: Request,
    livro_id: int,
    personagem_id: int,
    payload: PersonagemUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_auth)],
):
    """Update character name, gender, age, or voice during review."""
    personagem = (
        await db.execute(
            select(Personagem).where(
                Personagem.id == personagem_id,
                Personagem.livro_id == livro_id,
            )
        )
    ).scalar_one_or_none()

    if personagem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Personagem nao encontrado",
        )

    personagem.nome = payload.nome
    personagem.genero = payload.genero
    personagem.idade = payload.idade
    personagem.voz_id = payload.voz_id
    await db.flush()
    await db.refresh(personagem)

    # Build fala list for the partial
    rows = (
        await db.execute(
            select(Fala.id, Fala.texto, Pagina.numero)
            .join(Pagina, Fala.pagina_id == Pagina.id)
            .where(Fala.personagem_id == personagem.id)
            .order_by(Pagina.numero, Fala.id)
        )
    ).all()
    falas = [FalaResumo(id=r[0], texto=r[1], pagina_numero=r[2]) for r in rows]

    personagem_item = PersonagemItem(
        id=personagem.id,
        nome=personagem.nome,
        nome_original=personagem.nome_original,
        genero=personagem.genero,
        idade=personagem.idade,
        is_narrador=personagem.is_narrador,
        voz_id=personagem.voz_id,
        falas=falas,
    )

    if wants_html_partial(request):
        return templates.TemplateResponse(
            request=request,
            name="partials/revisao_personagem_updated.html",
            context={"request": request, "p": personagem_item},
        )

    return {"status": "atualizado", "personagem_id": personagem_id}


@router.post("/aprovar", status_code=status.HTTP_200_OK)
async def aprovar_revisao(
    request: Request,
    livro_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_auth)],
):
    """Approve review and resume processing."""
    from app.models.book_task import BookTask
    from app.services.livro_service import _enqueue_book_task

    result = await db.execute(
        select(Livro).where(
            Livro.id == livro_id,
            Livro.usuario_id == usuario.id,
        )
    )
    livro = result.scalar_one_or_none()
    if livro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro nao encontrado",
        )

    livro.status = "em_producao"

    task = (
        await db.execute(
            select(BookTask).where(BookTask.livro_id == livro_id)
        )
    ).scalar_one_or_none()
    if task:
        task.status = "em_producao"
    await db.flush()

    # Enqueue for audio production
    _enqueue_book_task(livro_id)

    if wants_html_partial(request):
        return templates.TemplateResponse(
            request=request,
            name="partials/revisao_aprovada.html",
            context={"request": request, "livro_id": livro_id},
        )
    return {"status": "em_producao"}
