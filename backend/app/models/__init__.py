"""SQLAlchemy models — import submodules explicitly to register tables."""

from app.models.base import Base

# Register all ORM tables with Alembic / metadata.create_all
from app.models.api_config import ApiConfig  # noqa: F401
from app.models.arquivo import Arquivo  # noqa: F401
from app.models.book_review import BookReview  # noqa: F401
from app.models.book_task import BookTask  # noqa: F401
from app.models.capitulo import Capitulo  # noqa: F401
from app.models.falas import Fala  # noqa: F401
from app.models.livro import Livro  # noqa: F401
from app.models.pagina import Pagina  # noqa: F401
from app.models.personagem import Personagem  # noqa: F401
from app.models.usuario import Usuario  # noqa: F401
from app.models.voz import Voz  # noqa: F401

__all__ = [
    "Base",
    "ApiConfig",
    "Arquivo",
    "BookReview",
    "BookTask",
    "Capitulo",
    "Fala",
    "Livro",
    "Pagina",
    "Personagem",
    "Usuario",
    "Voz",
]
