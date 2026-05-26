"""Render HTMX HTML partials for livro endpoints."""

from fastapi import Request
from starlette.responses import Response

from app.schemas.livro import LivroListItem, LivroProgresso
from app.templating import status_icon, templates


def render_livro_list(request: Request, livros: list[LivroListItem]) -> Response:
    """Render the book queue partial."""
    return templates.TemplateResponse(
        request=request,
        name="partials/livro_list.html",
        context={"request": request, "livros": livros},
    )


def render_livro_card(request: Request, livro: LivroListItem) -> Response:
    """Render a single book card (outerHTML swap)."""
    icon = status_icon(livro.status)
    return templates.TemplateResponse(
        request=request,
        name="partials/livro_card.html",
        context={"request": request, "livros": [livro], "livro": livro, "icon": icon},
    )


def render_progresso(request: Request, progresso: LivroProgresso) -> Response:
    """Render progress bar partial."""
    return templates.TemplateResponse(
        request=request,
        name="partials/progresso.html",
        context={
            "request": request,
            "progresso": progresso.progresso,
            "etapa": progresso.etapa,
        },
    )


def render_upload_success(
    request: Request, livro_id: int, status: str
) -> Response:
    """Render upload success alert."""
    return templates.TemplateResponse(
        request=request,
        name="partials/upload_success.html",
        context={"request": request, "livro_id": livro_id, "status": status},
    )
