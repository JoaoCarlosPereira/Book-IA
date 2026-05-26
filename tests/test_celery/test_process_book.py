"""Tests for Celery process_book pipeline orchestration."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.ia import CharacterProfile  # noqa: E402
from app.services.pdf_processor import Page, PageExtractionResult  # noqa: E402

STAGE_AUDIO = "AUDIO_PRODUCTION"
STAGE_IA = "IA_ANALYSIS"
STAGE_MUSIC = "MUSICGEN"
STAGE_PDF = "PDF_PROCESSING"
STAGE_UNIFICAR = "UNIFICAR"
STAGE_VOZ = "VOICE_ASSIGNMENT"
from app.models.book_task import BookTask  # noqa: E402
from app.models.livro import Livro  # noqa: E402
from app.models.pagina import Pagina  # noqa: E402
from app.models.personagem import Personagem  # noqa: E402
from app.models.usuario import Usuario  # noqa: E402
from app.models.voz import Voz  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture()
def sync_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    usuario = Usuario(login="tester", senha_hash="hash", perfil="admin")
    session.add(usuario)
    session.flush()
    livro = Livro(
        titulo="Livro Teste",
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


class TestParseExtracaoLinhas:
    def test_parse_nome_fala(self, fresh_process_book_module) -> None:
        raw = "narrator|Ele caminhava pela floresta.\njoao|Olá, mundo."
        linhas = fresh_process_book_module._parse_extracao_linhas(raw)
        assert linhas == [
            ("narrator", "Ele caminhava pela floresta."),
            ("joao", "Olá, mundo."),
        ]

    def test_ignora_no_characters(self, fresh_process_book_module) -> None:
        assert fresh_process_book_module._parse_extracao_linhas("no characters") == []


class TestMatchVoz:
    def test_match_genero_idade(self, sync_db: Session, fresh_process_book_module) -> None:
        vozes = sync_db.query(Voz).all()
        voz_id = fresh_process_book_module._match_voz(vozes, "feminino", "adulto")
        assert voz_id == vozes[1].id

    def test_fallback_genero(self, sync_db: Session, fresh_process_book_module) -> None:
        vozes = sync_db.query(Voz).all()
        voz_id = fresh_process_book_module._match_voz(vozes, "feminino", "idoso")
        assert voz_id == vozes[1].id


class TestStagePdfProcessing:
    def test_extrai_e_salva_paginas(
        self, sync_db: Session, tmp_path: Path, fresh_process_book_module
    ) -> None:
        pdf_path = tmp_path / "livro.pdf"
        pdf_path.write_text("dummy")
        livro = sync_db.query(Livro).first()
        livro.caminho_pdf = str(pdf_path)
        sync_db.commit()

        pb = fresh_process_book_module
        pipeline = pb.BookPipeline(sync_db, _livro_id(sync_db), tmp_path / "work")
        extraction = PageExtractionResult(
            pages=[
                Page(numero=1, texto="Página um."),
                Page(numero=2, texto="Página dois."),
            ]
        )

        with patch.object(
            pb.PDFProcessor,
            "extract_text",
            return_value=extraction,
        ):
            pipeline._stage_pdf_processing()

        paginas = sync_db.query(Pagina).filter(Pagina.livro_id == livro.id).all()
        assert len(paginas) == 2
        assert paginas[0].texto == "Página um."
        task = sync_db.query(BookTask).filter(BookTask.livro_id == livro.id).first()
        assert task.progresso == 10
        assert task.etapa_atual == STAGE_PDF


class TestStageIaAnalysis:
    def test_personagens_normalizados_e_perfis(
        self, sync_db: Session, tmp_path: Path, fresh_process_book_module
    ) -> None:
        livro_id = _livro_id(sync_db)
        sync_db.add(Pagina(livro_id=livro_id, numero=1, texto="Texto da página.", processado=False))
        sync_db.commit()

        mock_analyzer = MagicMock()
        mock_analyzer._chamar_llm = AsyncMock(
            return_value="narrator|Narração longa.\njoao|Fala do João."
        )
        mock_analyzer.normalizar_nomes = AsyncMock(
            return_value=[
                CharacterProfile(nome="narrator", genero="masculino", idade="adulto"),
                CharacterProfile(nome="joao", genero="masculino", idade="adulto"),
            ]
        )
        mock_analyzer.definir_perfil = AsyncMock(
            side_effect=lambda texto, nome: CharacterProfile(
                nome=nome, genero="masculino", idade="adulto"
            )
        )
        mock_analyzer.aclose = AsyncMock()

        pb = fresh_process_book_module
        pipeline = pb.BookPipeline(sync_db, livro_id, tmp_path / "work")
        with patch.object(pb, "_load_ia_analyzer", return_value=mock_analyzer):
            pipeline._stage_ia_analysis()

        personagens = (
            sync_db.query(Personagem).filter(Personagem.livro_id == livro_id).all()
        )
        nomes = {p.nome for p in personagens}
        assert "narrator" in nomes
        assert "joao" in nomes
        task = sync_db.query(BookTask).filter(BookTask.livro_id == livro_id).first()
        assert task.progresso == 40
        assert task.etapa_atual == STAGE_IA


class TestStageVoiceAssignment:
    def test_atribui_voz_por_genero_idade(
        self, sync_db: Session, tmp_path: Path, fresh_process_book_module
    ) -> None:
        livro_id = _livro_id(sync_db)
        sync_db.add(
            Personagem(
                livro_id=livro_id,
                nome="maria",
                genero="feminino",
                idade="adulto",
                is_narrador=False,
            )
        )
        sync_db.commit()

        pipeline = fresh_process_book_module.BookPipeline(
            sync_db, livro_id, tmp_path / "work"
        )
        pipeline._stage_voice_assignment()

        maria = (
            sync_db.query(Personagem)
            .filter(Personagem.livro_id == livro_id, Personagem.nome == "maria")
            .first()
        )
        voz_fem = (
            sync_db.query(Voz).filter(Voz.genero == "feminino", Voz.idade == "adulto").first()
        )
        assert maria.voz_id == voz_fem.id
        task = sync_db.query(BookTask).filter(BookTask.livro_id == livro_id).first()
        assert task.progresso == 50
        assert task.etapa_atual == STAGE_VOZ


class TestStageAudioProduction:
    def test_gera_audio_para_falas(
        self, sync_db: Session, tmp_path: Path, fresh_process_book_module
    ) -> None:
        livro_id = _livro_id(sync_db)
        pagina = Pagina(livro_id=livro_id, numero=1, texto="x", processado=True)
        sync_db.add(pagina)
        sync_db.flush()
        personagem = Personagem(
            livro_id=livro_id,
            nome="narrator",
            genero="masculino",
            idade="adulto",
            is_narrador=True,
            voz_id=sync_db.query(Voz).first().id,
        )
        sync_db.add(personagem)
        sync_db.flush()
        from app.models.falas import Fala

        sync_db.add(
            Fala(
                livro_id=livro_id,
                pagina_id=pagina.id,
                personagem_id=personagem.id,
                texto="Narração de teste.",
                processado=False,
            )
        )
        sync_db.commit()

        mp3 = tmp_path / "chunk.mp3"
        mp3.write_bytes(b"mp3")

        mock_tts = MagicMock()
        mock_tts.gerar_audio = AsyncMock(return_value=str(mp3))
        mock_tts.aclose = AsyncMock()

        pb = fresh_process_book_module
        pipeline = pb.BookPipeline(sync_db, livro_id, tmp_path / "work")
        with patch.object(pb, "_load_tts_engine", return_value=mock_tts):
            pipeline._stage_audio_production()

        assert len(pipeline._audio_paths) == 1
        task = sync_db.query(BookTask).filter(BookTask.livro_id == livro_id).first()
        assert task.progresso == 90
        assert task.etapa_atual == STAGE_AUDIO

    def test_falha_marca_status_falhou(
        self, sync_db: Session, tmp_path: Path, fresh_process_book_module
    ) -> None:
        livro_id = _livro_id(sync_db)
        pagina = Pagina(livro_id=livro_id, numero=1, texto="x", processado=True)
        sync_db.add(pagina)
        sync_db.flush()
        personagem = Personagem(
            livro_id=livro_id,
            nome="narrator",
            is_narrador=True,
            voz_id=sync_db.query(Voz).first().id,
        )
        sync_db.add(personagem)
        sync_db.flush()
        from app.models.falas import Fala

        sync_db.add(
            Fala(
                livro_id=livro_id,
                pagina_id=pagina.id,
                personagem_id=personagem.id,
                texto="texto",
                processado=False,
            )
        )
        sync_db.commit()

        mock_tts = MagicMock()
        mock_tts.gerar_audio = AsyncMock(side_effect=RuntimeError("TTS indisponível"))
        mock_tts.aclose = AsyncMock()

        pb = fresh_process_book_module
        pipeline = pb.BookPipeline(sync_db, livro_id, tmp_path / "work")
        with patch.object(pb, "_load_tts_engine", return_value=mock_tts), patch.object(
            pipeline, "_stage_pdf_processing"
        ), patch.object(pipeline, "_stage_ia_analysis"), patch.object(
            pipeline, "_stage_voice_assignment"
        ):
            with pytest.raises(RuntimeError, match="TTS indisponível"):
                pipeline.run()

        task = sync_db.query(BookTask).filter(BookTask.livro_id == livro_id).first()
        livro = sync_db.get(Livro, livro_id)
        assert task.status == "falhou"
        assert "TTS indisponível" in (task.erro or "")
        assert livro.status == "falhou"


class TestStageMusicgen:
    def test_basico_pula_trilha(
        self, sync_db: Session, tmp_path: Path, fresh_process_book_module
    ) -> None:
        livro_id = _livro_id(sync_db)
        pipeline = fresh_process_book_module.BookPipeline(
            sync_db, livro_id, tmp_path / "work"
        )
        pipeline._stage_musicgen()
        assert pipeline._trilha_paths == []
        task = sync_db.query(BookTask).filter(BookTask.livro_id == livro_id).first()
        assert task.progresso == 95

    def test_avancado_gera_trilha(
        self, sync_db: Session, tmp_path: Path, fresh_process_book_module
    ) -> None:
        livro_id = _livro_id(sync_db)
        livro = sync_db.get(Livro, livro_id)
        livro.nivel_producao = "avancado"
        sync_db.add(Pagina(livro_id=livro_id, numero=1, texto="Cena tensa.", processado=True))
        sync_db.commit()

        mock_music = MagicMock()
        mock_music.gerar_trilhas_livro = AsyncMock(return_value=["/tmp/trilha.wav"])
        mock_music.aclose = AsyncMock()

        pb = fresh_process_book_module
        pipeline = pb.BookPipeline(sync_db, livro_id, tmp_path / "work")
        with patch.object(
            pb, "_load_ia_analyzer", return_value=MagicMock(aclose=AsyncMock())
        ), patch.object(pb, "_load_musicgen", return_value=mock_music):
            pipeline._stage_musicgen()

        mock_music.gerar_trilhas_livro.assert_awaited_once()
        assert pipeline._trilha_paths == ["/tmp/trilha.wav"]
        task = sync_db.query(BookTask).filter(BookTask.livro_id == livro_id).first()
        assert task.etapa_atual == STAGE_MUSIC


class TestStageUnificar:
    def test_unifica_e_conclui(
        self, sync_db: Session, tmp_path: Path, fresh_process_book_module
    ) -> None:
        livro_id = _livro_id(sync_db)
        mp3_a = tmp_path / "a.mp3"
        mp3_b = tmp_path / "b.mp3"
        mp3_a.write_bytes(b"a")
        mp3_b.write_bytes(b"b")

        pb = fresh_process_book_module
        pipeline = pb.BookPipeline(sync_db, livro_id, tmp_path / "work")
        pipeline._audio_paths = [mp3_a, mp3_b]

        mock_tts = MagicMock()
        mock_tts._unificar_arquivos = MagicMock(
            side_effect=lambda arquivos, dest: dest.write_bytes(b"final") or dest
        )

        with patch.object(pb, "_load_tts_engine", return_value=mock_tts), patch.object(
            pb.settings, "audio_dir", str(tmp_path / "audio")
        ):
            pipeline._stage_unificar()

        livro = sync_db.get(Livro, livro_id)
        assert livro.caminho_audio
        assert Path(livro.caminho_audio).exists()
        task = sync_db.query(BookTask).filter(BookTask.livro_id == livro_id).first()
        assert task.progresso == 100
        assert task.etapa_atual == STAGE_UNIFICAR


class TestPipelinePaused:
    def test_para_quando_pausado(
        self, sync_db: Session, tmp_path: Path, fresh_process_book_module
    ) -> None:
        livro_id = _livro_id(sync_db)
        task = sync_db.query(BookTask).filter(BookTask.livro_id == livro_id).first()
        task.status = "pausado"
        sync_db.commit()

        pipeline = fresh_process_book_module.BookPipeline(
            sync_db, livro_id, tmp_path / "work"
        )
        with patch.object(pipeline, "_stage_pdf_processing") as mock_pdf:
            result = pipeline.run()
        mock_pdf.assert_not_called()
        assert result == f"livro_{livro_id}_pausado"


class TestFullPipelineMocked:
    def test_pipeline_completo_basico(
        self, sync_db: Session, tmp_path: Path, fresh_process_book_module
    ) -> None:
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
            return_value="narrator|Narração completa do livro."
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
            side_effect=lambda arquivos, dest: dest.write_bytes(b"ok") or dest
        )

        extraction = PageExtractionResult(
            pages=[Page(numero=1, texto="Conteúdo da página.")]
        )

        pb = fresh_process_book_module
        pipeline = pb.BookPipeline(sync_db, livro_id, tmp_path / "work")
        with patch.object(
            pb.PDFProcessor, "extract_text", return_value=extraction
        ), patch.object(pb, "_load_ia_analyzer", return_value=mock_analyzer), patch.object(
            pb, "_load_tts_engine", return_value=mock_tts
        ), patch.object(pb.settings, "audio_dir", str(tmp_path / "audio")):
            result = pipeline.run()

        assert result == f"livro_{livro_id}_processed"
        livro = sync_db.get(Livro, livro_id)
        task = sync_db.query(BookTask).filter(BookTask.livro_id == livro_id).first()
        assert livro.status == "concluido"
        assert task.status == "concluido"
        assert task.progresso == 100
        assert livro.caminho_audio
