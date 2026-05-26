"""Auth API routes (v1): setup, login, logout."""

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_db
from app.models.usuario import Usuario
from app.services.auth_service import hash_password, session_store, verify_password
from app.templating import templates

router = APIRouter(prefix="/auth", tags=["auth"])


def _wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    content_type = request.headers.get("content-type", "")
    return "application/json" in accept or "application/json" in content_type


def _set_session_cookie(response: Response, session_id: str) -> None:
    max_age = settings.session_idle_timeout_minutes * 60
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=max_age,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
    )


def _redirect_with_session(url: str, session_id: str) -> RedirectResponse:
    response = RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    _set_session_cookie(response, session_id)
    return response


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str | None = None) -> HTMLResponse:
    """Render the login page (Pac-Man Tech Theme)."""
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": error == "1"},
    )


@router.post("/login")
async def login(
    request: Request,
    login: str = Form(...),
    senha: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Validate credentials, create session, set HTTP-only cookie."""
    result = await db.execute(select(Usuario).where(Usuario.login == login))
    usuario = result.scalar_one_or_none()

    if usuario is None or not verify_password(senha, usuario.senha_hash):
        if _wants_json(request):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Login ou senha inválidos.",
            )
        return RedirectResponse(
            url="/login?error=1",
            status_code=status.HTTP_302_FOUND,
        )

    session_id = session_store.create(usuario.id)
    return _redirect_with_session("/dashboard", session_id)


@router.post("/logout")
async def logout(request: Request) -> Response:
    """Destroy session and clear cookie."""
    session_id = request.cookies.get(settings.session_cookie_name)
    session_store.destroy(session_id)

    response = RedirectResponse(
        url="/login",
        status_code=status.HTTP_302_FOUND,
    )
    _clear_session_cookie(response)
    return response


@router.post("/setup")
async def setup(
    request: Request,
    login: str = Form(...),
    senha: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Create the first admin user when no users exist."""
    count_result = await db.execute(select(func.count()).select_from(Usuario))
    user_count = count_result.scalar_one()

    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="O sistema já possui um administrador configurado.",
        )

    if len(senha) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha deve ter pelo menos 6 caracteres.",
        )

    usuario = Usuario(
        login=login,
        senha_hash=hash_password(senha),
        perfil="admin",
    )
    db.add(usuario)
    await db.flush()
    await db.refresh(usuario)

    session_id = session_store.create(usuario.id)

    if _wants_json(request):
        response = JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "id": usuario.id,
                "login": usuario.login,
                "perfil": usuario.perfil,
            },
        )
        _set_session_cookie(response, session_id)
        return response

    return _redirect_with_session("/dashboard", session_id)
