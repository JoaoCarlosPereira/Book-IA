"""Session authentication middleware for protected HTML routes."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from app.config import settings
from app.services.auth_service import session_store


class SessionAuthMiddleware(BaseHTTPMiddleware):
    """Redirect unauthenticated users away from protected paths."""

    PUBLIC_EXACT: frozenset[str] = frozenset(
        {
            "/",
            "/health",
            "/health/redis",
            "/health/celery",
            "/login",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
    )

    PUBLIC_PREFIXES: tuple[str, ...] = (
        "/api/v1/auth",
        "/static",
    )

    PROTECTED_PREFIXES: tuple[str, ...] = (
        "/dashboard",
        "/livros",
        "/configuracoes",
        "/api/v1/livros",
        "/api/v1/configuracoes",
        "/api/v1/tarefas",
    )

    def _is_public(self, path: str) -> bool:
        if path in self.PUBLIC_EXACT:
            return True
        return any(path.startswith(prefix) for prefix in self.PUBLIC_PREFIXES)

    def _is_protected(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.PROTECTED_PREFIXES)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        if self._is_public(path) or not self._is_protected(path):
            return await call_next(request)

        api_token = request.headers.get("x-auth-token")
        if api_token and api_token == settings.secret_key:
            return await call_next(request)

        session_id = request.cookies.get(settings.session_cookie_name)
        user_id = session_store.validate(session_id)

        if user_id is None:
            accept = request.headers.get("accept", "")
            if "application/json" in accept and "text/html" not in accept:
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Autenticação necessária. Faça login novamente.",
                    },
                )
            return RedirectResponse(url="/login", status_code=302)

        request.state.user_id = user_id
        return await call_next(request)
