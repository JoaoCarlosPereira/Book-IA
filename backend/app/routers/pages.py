"""HTML page routes (Jinja2 + HTMX dashboard)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_auth
from app.models.usuario import Usuario
from app.schemas.api_config import ApiConfigCreate, ApiConfigUpdate
from app.services.api_config_service import ApiConfigService, _to_response_dict
from app.services.livro_service import LivroService
from app.templating import templates

router = APIRouter(tags=["pages"])


@router.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect home to dashboard."""
    return RedirectResponse(url="/dashboard", status_code=302)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    usuario: Annotated[Usuario, Depends(require_auth)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HTMLResponse:
    """Main queue dashboard with HTMX polling."""
    data = await LivroService(db).listar(usuario.id)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"request": request, "usuario": usuario, "livros": data.items},
    )


@router.get("/livros/upload", response_class=HTMLResponse)
async def upload_page(
    request: Request,
    usuario: Annotated[Usuario, Depends(require_auth)],
) -> HTMLResponse:
    """Upload form page."""
    return templates.TemplateResponse(
        request=request,
        name="livro/upload.html",
        context={"request": request, "usuario": usuario},
    )


@router.get("/livros/{livro_id}", response_class=HTMLResponse)
async def livro_detail_page(
    request: Request,
    livro_id: int,
    usuario: Annotated[Usuario, Depends(require_auth)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HTMLResponse:
    """Book detail page with tabs."""
    livro = await LivroService(db).obter_detalhe(livro_id, usuario.id)
    return templates.TemplateResponse(
        request=request,
        name="livro/detail.html",
        context={"request": request, "usuario": usuario, "livro": livro},
    )


@router.get("/livros/{livro_id}/revisao", response_class=HTMLResponse)
async def livro_revisao_page(
    request: Request,
    livro_id: int,
    usuario: Annotated[Usuario, Depends(require_auth)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HTMLResponse:
    """Book character review page (Fase 2)."""
    from app.models.personagem import Personagem
    from app.models.voz import Voz

    livro_result = await db.execute(
        select(Livro).where(Livro.id == livro_id, Livro.usuario_id == usuario.id)
    )
    livro = livro_result.scalar_one_or_none()
    if livro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro nao encontrado",
        )

    personagens = (
        await db.execute(
            select(Personagem).where(Personagem.livro_id == livro_id)
        )
    ).scalars().all()

    vozes = (
        await db.execute(select(Voz))
    ).scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="livro/review.html",
        context={
            "request": request,
            "usuario": usuario,
            "livro": livro,
            "personagens": personagens,
            "vozes": vozes,
        },
    )


@router.get("/configuracoes", response_class=HTMLResponse)
async def configuracoes_page(
    request: Request,
    usuario: Annotated[Usuario, Depends(require_auth)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HTMLResponse:
    """API configuration panel."""
    rows = await ApiConfigService(db).list_configs(incluir_inativos=True)
    apis = [_to_response_dict(r) for r in rows]
    return templates.TemplateResponse(
        request=request,
        name="livro/configuracoes.html",
        context={"request": request, "usuario": usuario, "apis": apis},
    )


@router.post("/configuracoes/apis", response_class=HTMLResponse)
async def criar_api_form(
    request: Request,
    usuario: Annotated[Usuario, Depends(require_auth)],
    db: Annotated[AsyncSession, Depends(get_db)],
    tipo: str = Form(...),
    modo: str = Form(...),
    url: str = Form(...),
    token: str | None = Form(default=None),
    modelo: str | None = Form(default=None),
) -> RedirectResponse:
    """Create API config from HTML form."""
    body = ApiConfigCreate(
        tipo=tipo,  # type: ignore[arg-type]
        modo=modo,  # type: ignore[arg-type]
        url=url,
        token=token or None,
        modelo=modelo or None,
        ativo=True,
    )
    await ApiConfigService(db).create(body)
    return RedirectResponse(url="/configuracoes", status_code=303)


@router.post("/configuracoes/apis/{config_id}", response_class=HTMLResponse)
async def atualizar_api_form(
    request: Request,
    config_id: int,
    usuario: Annotated[Usuario, Depends(require_auth)],
    db: Annotated[AsyncSession, Depends(get_db)],
    modo: str = Form(...),
    url: str = Form(...),
    token: str | None = Form(default=None),
    modelo: str | None = Form(default=None),
    ativo: str | None = Form(default=None),
) -> RedirectResponse:
    """Update API config from HTML form."""
    body = ApiConfigUpdate(
        modo=modo,  # type: ignore[arg-type]
        url=url,
        token=token if token else None,
        modelo=modelo or None,
        ativo=ativo == "true",
    )
    try:
        await ApiConfigService(db).update(config_id, body)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return RedirectResponse(url="/configuracoes", status_code=303)
