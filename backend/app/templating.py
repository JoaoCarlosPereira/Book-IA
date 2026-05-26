"""Shared Jinja2 templates for HTML and HTMX responses."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# Semantic status colors (Pac-Man Tech Theme — TechSpec)
STATUS_BADGE_CLASS: dict[str, str] = {
    "pendente": "status-badge-pendente",
    "processando": "status-badge-processando",
    "concluido": "status-badge-concluido",
    "concluído": "status-badge-concluido",
    "falhou": "status-badge-falhou",
    "pausado": "status-badge-pausado",
    "cancelado": "status-badge-cancelado",
}

STATUS_ICONS: dict[str, str] = {
    "pendente": "bi-hourglass-split",
    "processando": "bi-arrow-repeat",
    "concluido": "bi-check-circle",
    "concluído": "bi-check-circle",
    "falhou": "bi-x-circle",
    "pausado": "bi-pause-circle",
    "cancelado": "bi-slash-circle",
}


def status_badge_class(status: str) -> str:
    """Return CSS class for a processing status badge."""
    return STATUS_BADGE_CLASS.get(status.lower(), "status-badge-pendente")


def status_icon(status: str) -> str:
    """Return Bootstrap Icons class for a processing status."""
    return STATUS_ICONS.get(status.lower(), "bi-book")


templates.env.globals["status_badge_class"] = status_badge_class
templates.env.globals["status_icon"] = status_icon
