"""Book-IA: FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import auth, capitulos, configuracoes, livros, tarefas, revisao
from app.config import settings
from app.middlewares.session import SessionAuthMiddleware
from app.routers import pages

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_DESIGN_DIR = _REPO_ROOT / "design"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    yield


app = FastAPI(
    title="Book-IA API",
    description="Serviço web de conversão de PDF em audiobook com IA",
    version="0.1.0",
    lifespan=lifespan,
)

# Static assets (Pac-Man Tech Theme)
_static_path = _STATIC_DIR if _STATIC_DIR.is_dir() else _DESIGN_DIR
if _static_path.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static_path)), name="static")

# Session protection for HTML routes and protected API prefixes
app.add_middleware(SessionAuthMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(url) for url in settings.cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(livros.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(configuracoes.router, prefix="/api/v1")
app.include_router(tarefas.router, prefix="/api/v1")
app.include_router(tarefas.health_router)
app.include_router(revisao.router, prefix="/api/v1")
app.include_router(capitulos.router, prefix="/api/v1")
app.include_router(pages.router)


@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok"})


@app.get("/login", include_in_schema=False)
async def login_redirect(request: Request):
    """Alias for the login page."""
    url = "/api/v1/auth/login"
    if request.query_params.get("error"):
        url = f"{url}?error=1"
    return RedirectResponse(url=url, status_code=302)
