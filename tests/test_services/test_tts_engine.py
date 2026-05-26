"""Unit tests for TTSEngine (chunking, TTS API, ffmpeg)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.tts_engine import (
    TTSAPIError,
    TTSEngine,
    _sanitizar_nome,
    chunkar_texto,
)


@pytest.fixture()
def engine(tmp_path: Path) -> TTSEngine:
    return TTSEngine(
        api_url="http://tts.test:8001",
        api_key="test-token",
        audio_dir=tmp_path / "audio",
        timeout=5.0,
    )


class TestChunkarTexto:
    def test_divide_por_sentenca(self) -> None:
        texto = (
            "Primeira sentença com bastante conteúdo narrativo. "
            "Segunda sentença também longa o suficiente para forçar nova divisão. "
            "Terceira sentença fecha o parágrafo com mais detalhes."
        )
        chunks = chunkar_texto(texto, max_chars=80)
        assert len(chunks) >= 2
        assert all(len(c) <= 80 for c in chunks)

    def test_texto_longo_gera_multiplos_chunks(self) -> None:
        paragrafo = " ".join(["Palavra"] * 120) + "."
        texto = (paragrafo + " ") * 5
        chunks = chunkar_texto(texto.strip(), max_chars=180)
        assert len(chunks) > 1
        assert all(len(c) <= 180 for c in chunks)

    def test_sem_ponto_divide_por_palavra(self) -> None:
        texto = " ".join(["termo"] * 80)
        chunks = chunkar_texto(texto, max_chars=50)
        assert len(chunks) > 1
        assert all(" " in c or len(c) <= 50 for c in chunks)

    def test_ponto_isolado_vira_virgula(self) -> None:
        chunks = chunkar_texto(".", max_chars=180)
        assert chunks == [","]

    def test_substituicao_ponto_em_chunk(self) -> None:
        chunks = chunkar_texto("Olá mundo.", max_chars=180)
        assert chunks
        assert "." not in chunks[0]
        assert "," in chunks[0]

    def test_exatamente_180_chars_um_chunk(self) -> None:
        texto = "a" * 180
        chunks = chunkar_texto(texto, max_chars=180)
        assert len(chunks) == 1
        assert len(chunks[0].replace(" ,", ",")) >= 180

    def test_179_chars_um_chunk(self) -> None:
        texto = "b" * 179
        chunks = chunkar_texto(texto, max_chars=180)
        assert len(chunks) == 1

    def test_texto_vazio(self) -> None:
        assert chunkar_texto("") == []
        assert chunkar_texto("   ") == []


class TestPostToTtsApi:
    @pytest.mark.asyncio
    async def test_salva_wav_do_corpo_da_resposta(self, engine: TTSEngine) -> None:
        wav_bytes = b"RIFFfake-wav-content"
        mock_response = httpx.Response(
            200,
            content=wav_bytes,
            headers={"content-type": "audio/wav"},
            request=httpx.Request("POST", "http://tts.test/generate-from-text"),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        engine._http_client = mock_client

        destino = Path("/tmp/test_chunk.wav")
        with patch.object(Path, "mkdir"), patch.object(Path, "write_bytes") as mock_write:
            resultado = await engine._post_to_tts_api(
                "texto teste,",
                ref_audio="voz1",
                output_wav=destino,
            )

        assert resultado == destino
        mock_write.assert_called_once_with(wav_bytes)

    @pytest.mark.asyncio
    async def test_tts_http_500_retry_3x(self, engine: TTSEngine) -> None:
        mock_response = httpx.Response(
            500,
            text="internal error",
            request=httpx.Request("POST", "http://tts.test/generate-from-text"),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        engine._http_client = mock_client

        with patch("app.services.tts_engine.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(TTSAPIError, match="3 tentativas"):
                await engine._post_to_tts_api(
                    "fala,",
                    ref_audio="",
                    output_wav=Path("/tmp/x.wav"),
                )

        assert mock_client.post.await_count == 3

    @pytest.mark.asyncio
    async def test_retry_3x_e_erro(self, engine: TTSEngine) -> None:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("conexão recusada", request=MagicMock())
        )
        engine._http_client = mock_client

        with patch("app.services.tts_engine.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(TTSAPIError, match="3 tentativas"):
                await engine._post_to_tts_api(
                    "fala,",
                    ref_audio="",
                    output_wav=Path("/tmp/x.wav"),
                )

        assert mock_client.post.await_count == 3


class TestFfmpeg:
    def test_converter_wav_para_mp3(self, engine: TTSEngine, tmp_path: Path) -> None:
        wav = tmp_path / "a.wav"
        wav.write_bytes(b"wav")
        mp3 = tmp_path / "a.mp3"

        with patch("app.services.tts_engine.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            resultado = engine._converter_wav_para_mp3(wav)

        assert resultado == mp3
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "ffmpeg"
        assert str(wav) in args
        assert str(mp3) in args

    def test_unificar_multiplos_mp3(self, engine: TTSEngine, tmp_path: Path) -> None:
        mp3_a = tmp_path / "a.mp3"
        mp3_b = tmp_path / "b.mp3"
        mp3_a.write_bytes(b"mp3a")
        mp3_b.write_bytes(b"mp3b")
        destino = tmp_path / "final.mp3"

        with patch("app.services.tts_engine.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            engine._unificar_arquivos([mp3_a, mp3_b], destino)

        mock_run.assert_called_once()
        comando = mock_run.call_args[0][0]
        assert "concat" in comando

    def test_unificar_arquivo_unico_copia(self, engine: TTSEngine, tmp_path: Path) -> None:
        unico = tmp_path / "only.mp3"
        unico.write_bytes(b"data")
        destino = tmp_path / "out.mp3"

        resultado = engine._unificar_arquivos([unico], destino)
        assert resultado == destino
        assert destino.read_bytes() == b"data"


class TestGerarAudio:
    @pytest.mark.asyncio
    async def test_pipeline_retorna_mp3(self, engine: TTSEngine) -> None:
        wav_response = httpx.Response(
            200,
            content=b"RIFF-wav",
            headers={"content-type": "audio/wav"},
            request=httpx.Request("POST", "http://tts.test/generate-from-text"),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=wav_response)
        engine._http_client = mock_client

        def fake_ffmpeg(cmd: list[str], **kwargs: object) -> MagicMock:
            saida = cmd[-1]
            Path(saida).write_bytes(b"MP3")
            return MagicMock(returncode=0)

        with patch("app.services.tts_engine.subprocess.run", side_effect=fake_ffmpeg):
            caminho = await engine.gerar_audio(
                "Uma frase curta para teste.",
                "Narrador",
            )

        assert caminho.endswith(".mp3")
        assert Path(caminho).exists()
        assert Path(caminho).read_bytes() == b"MP3"
        assert mock_client.post.await_count >= 1

    @pytest.mark.asyncio
    async def test_registra_arquivo_quando_livro_id(
        self,
        engine: TTSEngine,
        db_session,
    ) -> None:
        from app.models.livro import Livro
        from app.models.usuario import Usuario
        from app.services.auth_service import hash_password

        usuario = Usuario(login="tts_user", senha_hash=hash_password("senha123"))
        db_session.add(usuario)
        await db_session.flush()

        livro = Livro(
            titulo="Livro Teste",
            nome_arquivo="livro.pdf",
            tipo_documento="pdf",
            nivel_producao="basico",
            status="processando",
            usuario_id=usuario.id,
        )
        db_session.add(livro)
        await db_session.flush()

        wav_response = httpx.Response(
            200,
            content=b"RIFF",
            headers={"content-type": "audio/wav"},
            request=httpx.Request("POST", "http://tts.test/generate-from-text"),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=wav_response)
        engine._http_client = mock_client

        def fake_ffmpeg(cmd: list[str], **kwargs: object) -> MagicMock:
            Path(cmd[-1]).write_bytes(b"MP3")
            return MagicMock(returncode=0)

        with patch("app.services.tts_engine.subprocess.run", side_effect=fake_ffmpeg):
            caminho = await engine.gerar_audio(
                "Texto.",
                "Personagem A",
                livro_id=livro.id,
                db=db_session,
            )

        from sqlalchemy import select

        from app.models.arquivo import Arquivo

        result = await db_session.execute(
            select(Arquivo).where(Arquivo.livro_id == livro.id)
        )
        arquivo = result.scalar_one()
        assert arquivo.tipo == "mp3"
        assert arquivo.caminho == caminho


class TestHelpers:
    def test_sanitizar_nome(self) -> None:
        assert _sanitizar_nome("Personagem A!") == "Personagem_A_"
        assert _sanitizar_nome("   ") == "personagem"

    def test_headers_auth_com_token(self, engine: TTSEngine) -> None:
        headers = engine._headers_auth()
        assert headers["Authorization"] == "Bearer test-token"

    def test_headers_auth_sem_token(self, tmp_path: Path) -> None:
        engine_sem_key = TTSEngine(api_url="http://tts.test", audio_dir=tmp_path)
        assert engine_sem_key._headers_auth() == {}


class TestFromApiConfig:
    @pytest.mark.asyncio
    async def test_from_api_config_usa_settings_padrao(
        self, db_session
    ) -> None:
        from app.config import settings

        engine = await TTSEngine.from_api_config(db_session)
        assert settings.tts_api_url.rstrip("/") in engine.api_url

    @pytest.mark.asyncio
    async def test_from_api_config_com_row(
        self, db_session, db_factory
    ) -> None:
        from tests.factories import ApiConfigFactory, persist

        await persist(
            db_session,
            ApiConfigFactory,
            tipo="tts",
            modo="local",
            url="http://custom-tts:9001",
            token=None,
        )
        engine = await TTSEngine.from_api_config(db_session)
        assert engine.api_url == "http://custom-tts:9001"


class TestResolverWavJson:
    @pytest.mark.asyncio
    async def test_resposta_json_com_caminho(self, engine: TTSEngine, tmp_path: Path) -> None:
        destino = tmp_path / "out.wav"
        payload = {"output": str(destino)}
        mock_response = httpx.Response(
            200,
            json=payload,
            headers={"content-type": "application/json"},
            request=httpx.Request("POST", "http://tts.test/generate-from-text"),
        )
        destino.write_bytes(b"RIFF-json-wav")
        resultado = await engine._resolver_wav_resposta(mock_response, destino)
        assert resultado == destino


class TestContextManager:
    @pytest.mark.asyncio
    async def test_aclose_limpa_client(self, engine: TTSEngine) -> None:
        _ = engine._client()
        await engine.aclose()
        assert engine._http_client is None

    @pytest.mark.asyncio
    async def test_async_context_manager(self, tmp_path: Path) -> None:
        async with TTSEngine(
            api_url="http://tts.test",
            audio_dir=tmp_path,
        ) as eng:
            assert eng.api_url == "http://tts.test"
