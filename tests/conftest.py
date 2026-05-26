"""Global pytest configuration and fixtures."""

import sys
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import fitz
import pytest
from ebooklib import epub
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(BACKEND_DIR))

from app.deps import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402
from app.services.auth_service import session_store  # noqa: E402

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """Create tables, reset sessions/users before each test; drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_store.clear()
    async with test_session_factory() as session:
        await session.execute(delete(Usuario))
        await session.commit()

    yield

    session_store.clear()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with test_session_factory() as session:
        yield session


@pytest.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client against the FastAPI app (test DB + real session auth)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture()
async def authenticated_client(client: AsyncClient) -> AsyncClient:
    """Client with an active admin session cookie."""
    await client.post(
        "/api/v1/auth/setup",
        data={"login": "testadmin", "senha": "senha123"},
        headers={"Accept": "application/json"},
    )
    return client


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Directory with shared PDF/EPUB/TXT fixture files."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def fixture_pdf_10_pages(fixtures_dir: Path) -> Path:
    """PDF with 10 pages of extractable text."""
    path = fixtures_dir / "ten_pages.pdf"
    if path.exists():
        return path
    doc = fitz.open()
    for i in range(10):
        page = doc.new_page()
        page.insert_text((72, 72), f"Conteudo da pagina {i + 1}.")
    doc.save(path)
    doc.close()
    return path


@pytest.fixture(scope="session")
def fixture_epub_5_chapters(fixtures_dir: Path) -> Path:
    """EPUB with 5 document chapters."""
    path = fixtures_dir / "five_chapters.epub"
    if path.exists():
        return path
    book = epub.EpubBook()
    book.set_identifier("book-ia-fixture-5ch")
    book.set_title("Fixture Cinco Capitulos")
    book.set_language("pt")
    chapters = []
    for i in range(1, 6):
        ch = epub.EpubHtml(
            title=f"Capitulo {i}",
            file_name=f"cap_{i}.xhtml",
            lang="pt",
        )
        ch.content = (
            f"<html><body><h1>Capitulo {i}</h1>"
            f"<p>Texto do capitulo {i} com acentuacao.</p></body></html>"
        )
        book.add_item(ch)
        chapters.append(ch)
    book.toc = [(ch, []) for ch in chapters]
    book.spine = chapters
    book.add_item(epub.EpubNcx())
    epub.write_epub(str(path), book)
    return path


@pytest.fixture()
def fixture_txt_utf8(fixtures_dir: Path) -> Path:
    """UTF-8 TXT fixture with Portuguese accents."""
    return fixtures_dir / "sample.txt"


@pytest.fixture()
def fixture_txt_empty_content(fixtures_dir: Path) -> Path:
    """TXT with only whitespace (non-empty file, no pages)."""
    return fixtures_dir / "empty_content.txt"


@pytest.fixture()
def db_factory(db_session: AsyncSession) -> Generator[None, None, None]:
    """Attach async session to factory_boy factories for the current test."""
    from tests import factories

    for factory_cls in (
        factories.UsuarioFactory,
        factories.LivroFactory,
        factories.PaginaFactory,
        factories.VozFactory,
        factories.PersonagemFactory,
        factories.ApiConfigFactory,
        factories.BookTaskFactory,
        factories.ArquivoFactory,
        factories.FalaFactory,
        factories.BookReviewFactory,
    ):
        factory_cls._meta.sqlalchemy_session = db_session  # type: ignore[attr-defined]
    yield
    for factory_cls in (
        factories.UsuarioFactory,
        factories.LivroFactory,
        factories.PaginaFactory,
        factories.VozFactory,
        factories.PersonagemFactory,
        factories.ApiConfigFactory,
        factories.BookTaskFactory,
        factories.ArquivoFactory,
        factories.FalaFactory,
        factories.BookReviewFactory,
    ):
        factory_cls._meta.sqlalchemy_session = None  # type: ignore[attr-defined]


# HTMX headers used by integration tests (dashboard polling, partial swaps)
HTMX_HEADERS = {
    "HX-Request": "true",
    "HX-Target": "livro-list",
}


@pytest.fixture()
async def integration_client(authenticated_client: AsyncClient) -> AsyncClient:
    """Authenticated HTTP client for full integration flows."""
    return authenticated_client
