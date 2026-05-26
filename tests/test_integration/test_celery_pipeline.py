"""Integration tests: BookPipeline / process_book with all external services mocked."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models import Base  # noqa: E402
from app.models.book_task import BookTask  # noqa: E402
from app.models.falas import Fala  # noqa: E402
from app.models.livro import Livro  # noqa: E402
from app.models.pagina import Pagina  # noqa: E402
from app.models.personagem import Personagem  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402
from app.models.voz import Voz  # noqa: E402
from app.schemas.ia import CharacterProfile  # noqa: E402
from app.services.pdf_processor import Page, PageExtractionResult  # noqa: E402

STAGE_PDF = "PDF_PROCESSING"
STAGE_IA = "IA_ANALYSIS"
STAGE_VOZ = "VOICE_ASSIGNMENT"
STAGE_AUDIO = "AUDIO_PRODUCTION"
STAGE_MUSIC = "MUSICGEN"
STAGE_UNIFICAR = "UNIFICAR"


@pytest.fixture(autouse=True)
def fresh_process_book_module():
    import app.celery_tasks.process_book as process_book_module

    importlib.reload(process_book_module)
    yield process_book_module


@pytest.fixture()
def sync_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    usuario = Usuario(login="integration", senha_hash="hash", perfil="admin")
    session.add(usuario)
    session.flush()
    livro = Livro(
        titulo="Pipeline Integration",
        nome_arquivo="livro.pdf",
        tipo_documento="pdf",
        nivel_producao="basico",
        status="pendente",
        progresso=0,
        caminho_pdf="/tmp/livro.pdf",
        usuario_id=usuario.id,
    )
    session.add(livro)
    session.flush()
    session.add(
        BookTask(
            livro_id=livro.id,
            status="pendente",
            prioridade=5,
            progresso=0,
            etapa_atual="aguardando",
        )
    )
    session.add(Voz(nome="voz_masc_adulto", genero="masculino", idade="adulto"))
    session.add(Voz(nome="voz_fem_adulto", genero="feminino", idade="adulto"))
    session.commit()
    yield session
    session.close()


def _livro_id(session: Session) -> int:
    return session.query(Livro).first().id  # type: ignore[union-attr]


class TestCeleryPipelineIntegration:
    def test_pipeline_completo_seis_etapas_db(
        self,
        sync_db: Session,
        tmp_path: Path,
        fresh_process_book_module,
    ) -> None:
        """Run BookPipeline with mocks; verify DB state after all 6 stages."""
        livro_id = _livro_id(sync_db)
        pdf_path = tmp_path / "livro.pdf"
        pdf_path.write_text("pdf")
        livro = sync_db.get(Livro, livro_id)
        livro.caminho_pdf = str(pdf_path)
        sync_db.commit()

        mp3 = tmp_path / "fala.mp3"
        mp3.write_bytes(b"mp3")

        mock_analyzer = MagicMock()
        mock_analyzer._chamar_llm = AsyncMock(
            return_value="narrator|Narração completa do livro de integração."
        )
        mock_analyzer.normalizar_nomes = AsyncMock(
            return_value=[
                CharacterProfile(nome="narrator", genero="masculino", idade="adulto"),
            ]
        )
        mock_analyzer.definir_perfil = AsyncMock(
            return_value=CharacterProfile(nome="narrator", genero="masculino", idade="adulto")
        )
        mock_analyzer.aclose = AsyncMock()

        mock_tts = MagicMock()
        mock_tts.gerar_audio = AsyncMock(return_value=str(mp3))
        mock_tts.aclose = AsyncMock()
        mock_tts._unificar_arquivos = MagicMock(
            side_effect=lambda arquivos, dest: dest.write_bytes(b"audiobook") or dest
        )

        extraction = PageExtractionResult(
            pages=[Page(numero=1, texto="Conteúdo da página de integração.")]
        )

        pb = fresh_process_book_module
        pipeline = pb.BookPipeline(sync_db, livro_id, tmp_path / "work")

        stage_checks: list[str] = []

        original_pdf = pipeline._stage_pdf_processing
        original_ia = pipeline._stage_ia_analysis
        original_voz = pipeline._stage_voice_assignment
        original_audio = pipeline._stage_audio_production
        original_music = pipeline._stage_musicgen
        original_unificar = pipeline._stage_unificar

        def _wrap(stage_name: str, original):
            def _runner():
                original()
                task = (
                    sync_db.query(BookTask)
                    .filter(BookTask.livro_id == livro_id)
                    .first()
                )
                stage_checks.append(task.etapa_atual)

            return _runner

        pipeline._stage_pdf_processing = _wrap(STAGE_PDF, original_pdf)  # type: ignore[method-assign]
        pipeline._stage_ia_analysis = _wrap(STAGE_IA, original_ia)  # type: ignore[method-assign]
        pipeline._stage_voice_assignment = _wrap(STAGE_VOZ, original_voz)  # type: ignore[method-assign]
        pipeline._stage_audio_production = _wrap(STAGE_AUDIO, original_audio)  # type: ignore[method-assign]
        pipeline._stage_musicgen = _wrap(STAGE_MUSIC, original_music)  # type: ignore[method-assign]
        pipeline._stage_unificar = _wrap(STAGE_UNIFICAR, original_unificar)  # type: ignore[method-assign]

        with (
            patch.object(pb.PDFProcessor, "extract_text", return_value=extraction),
            patch.object(pb, "_load_ia_analyzer", return_value=mock_analyzer),
            patch.object(pb, "_load_tts_engine", return_value=mock_tts),
            patch.object(pb.settings, "audio_dir", str(tmp_path / "audio")),
        ):
            result = pipeline.run()

        assert result == f"livro_{livro_id}_processed"
        assert stage_checks == [
            STAGE_PDF,
            STAGE_IA,
            STAGE_VOZ,
            STAGE_AUDIO,
            STAGE_MUSIC,
            STAGE_UNIFICAR,
        ]

        paginas = sync_db.query(Pagina).filter(Pagina.livro_id == livro_id).all()
        assert len(paginas) >= 1

        personagens = (
            sync_db.query(Personagem).filter(Personagem.livro_id == livro_id).all()
        )
        assert len(personagens) >= 1
        assert any(p.voz_id is not None for p in personagens)

        falas = sync_db.query(Fala).filter(Fala.livro_id == livro_id).all()
        assert len(falas) >= 1

        livro = sync_db.get(Livro, livro_id)
        task = sync_db.query(BookTask).filter(BookTask.livro_id == livro_id).first()
        assert livro.status == "concluido"
        assert task.status == "concluido"
        assert task.progresso == 100
        assert livro.caminho_audio
        assert Path(livro.caminho_audio).exists()

    def test_run_process_book_entrypoint(
        self,
        sync_db: Session,
        tmp_path: Path,
        fresh_process_book_module,
    ) -> None:
        """run_process_book (Celery entrypoint) completes with mocked services."""
        livro_id = _livro_id(sync_db)
        pdf_path = tmp_path / "livro.pdf"
        pdf_path.write_text("pdf")
        livro = sync_db.get(Livro, livro_id)
        livro.caminho_pdf = str(pdf_path)
        sync_db.commit()

        mp3 = tmp_path / "chunk.mp3"
        mp3.write_bytes(b"x")

        mock_analyzer = MagicMock()
        mock_analyzer._chamar_llm = AsyncMock(return_value="narrator|Texto.")
        mock_analyzer.normalizar_nomes = AsyncMock(
            return_value=[
                CharacterProfile(nome="narrator", genero="masculino", idade="adulto"),
            ]
        )
        mock_analyzer.definir_perfil = AsyncMock(
            return_value=CharacterProfile(nome="narrator", genero="masculino", idade="adulto")
        )
        mock_analyzer.aclose = AsyncMock()

        mock_tts = MagicMock()
        mock_tts.gerar_audio = AsyncMock(return_value=str(mp3))
        mock_tts.aclose = AsyncMock()
        mock_tts._unificar_arquivos = MagicMock(
            side_effect=lambda arquivos, dest: dest.write_bytes(b"ok") or dest
        )

        extraction = PageExtractionResult(pages=[Page(numero=1, texto="Página.")])

        pb = fresh_process_book_module
        with (
            patch.object(pb, "SessionLocal", lambda: sync_db),
            patch.object(pb.PDFProcessor, "extract_text", return_value=extraction),
            patch.object(pb, "_load_ia_analyzer", return_value=mock_analyzer),
            patch.object(pb, "_load_tts_engine", return_value=mock_tts),
            patch.object(pb.settings, "audio_dir", str(tmp_path / "audio")),
        ):
            result = pb.run_process_book(livro_id, tmp_path / "work")

        assert result == f"livro_{livro_id}_processed"
        livro = sync_db.get(Livro, livro_id)
        assert livro.status == "concluido"
