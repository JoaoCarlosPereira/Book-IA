"""Dependency injection utilities for FastAPI."""

from collections.abc import AsyncGenerator, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import async_session_factory
from app.models.usuario import Usuario
from app.services.auth_service import session_store


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session and ensure it is closed afterwards."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario | None:
    """Extract the current user from the session cookie, if valid."""
    session_id = request.cookies.get(settings.session_cookie_name)
    user_id = session_store.validate(session_id)
    if user_id is None:
        return None

    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    return result.scalar_one_or_none()


async def require_auth(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    """Require a valid session; raise 401 if missing or invalid."""
    user = await get_current_user(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária.",
        )
    return user


def require_role(*roles: str) -> Callable[..., object]:
    """Factory returning a dependency that enforces user profile roles."""

    async def _check_role(
        user: Annotated[Usuario, Depends(require_auth)],
    ) -> Usuario:
        if user.perfil not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão negada para esta operação.",
            )
        return user

    return _check_role
