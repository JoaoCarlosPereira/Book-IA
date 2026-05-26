"""Unit tests for MusicGenService (prompt, API, per-page logic)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.ia_analyzer import (
    IAAnalyzer,
    IAAnalyzerError,
    _extrair_prompt_ingles,
)
from app.services.musicgen import (
    MusicGenAPIError,
    MusicGenPromptError,
    MusicGenService,
    PaginaExcerto,
)


@pytest.fixture()
def service(tmp_path: Path) -> MusicGenService:
    mock_analyzer = AsyncMock(spec=IAAnalyzer)
    return MusicGenService(
        api_url="http://musicgen.test:8002",
        api_key="test-token",
        ia_analyzer=mock_analyzer,
        audio_dir=tmp_path / "audio",
        timeout=5.0,
    )


class TestExtrairPromptIngles:
    def test_extrai_texto_entre_aspas(self) -> None:
        raw = (
            '"An atmospheric, suspenseful instrumental soundtrack with slow tempo '
            'and orchestral elements."'
        )
        assert "atmospheric" in _extrair_prompt_ingles(raw)

    def test_retorna_texto_sem_aspas(self) -> None:
        assert _extrair_prompt_ingles("cinematic orchestral tense") == (
            "cinematic orchestral tense"
        )


class TestGerarPromptAtmosferico:
    @pytest.mark.asyncio
    async def test_retorna_string_em_ingles(self, service: MusicGenService) -> None:
        service.ia_analyzer.gerar_prompt_atmosferico = AsyncMock(
            return_value="melancholic piano, slow tempo, minor key"
        )
        prompt = await service._gerar_prompt_atmosferico("trecho triste", 0, 300)
        assert prompt
        assert all(ord(c) < 128 for c in prompt)
        service.ia_analyzer.gerar_prompt_atmosferico.assert_awaited_once_with(
            "trecho triste",
            0,
            300,
        )

    @pytest.mark.asyncio
    async def test_prompt_diferente_por_texto(self, service: MusicGenService) -> None:
        async def fake_prompt(texto: str, t0: int, t1: int) -> str:
            if "triste" in texto:
                return "sad orchestral, minor key"
            return "uplifting strings, major key"

        service.ia_analyzer.gerar_prompt_atmosferico = AsyncMock(side_effect=fake_prompt)

        triste = await service._gerar_prompt_atmosferico("trecho triste", 0, 60)
        alegre = await service._gerar_prompt_atmosferico("trecho alegre e festivo", 0, 60)
        assert triste != alegre

    @pytest.mark.asyncio
    async def test_ia_indisponivel_levanta_erro(self, service: MusicGenService) -> None:
        service.ia_analyzer.gerar_prompt_atmosferico = AsyncMock(
            side_effect=IAAnalyzerError("LLM indisponível")
        )
        with pytest.raises(MusicGenPromptError, match="LLM indisponível"):
            await service._gerar_prompt_atmosferico("texto", 0, 10)


class TestResolverWav:
    @pytest.mark.asyncio
    async def test_resposta_json_com_wav_bytes(self, service: MusicGenService, tmp_path: Path) -> None:
        import base64

        wav = b"RIFF-bytes"
        payload = {"wav_bytes": base64.b64encode(wav).decode("ascii")}
        destino = tmp_path / "trilha.wav"
        response = httpx.Response(
            200,
            json=payload,
            headers={"content-type": "application/json"},
            request=httpx.Request("POST", "http://musicgen.test/generate-from-text"),
        )
        resultado = await service._resolver_wav_resposta(response, destino)
        assert resultado.read_bytes() == wav

    @pytest.mark.asyncio
    async def test_baixar_wav_via_url(self, service: MusicGenService, tmp_path: Path) -> None:
        destino = tmp_path / "download.wav"
        mock_response = httpx.Response(
            200,
            content=b"RIFF-download",
            request=httpx.Request("GET", "http://musicgen.test/files/x.wav"),
        )
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        service._http_client = mock_client

        resultado = await service._baixar_wav("files/x.wav", destino)
        assert resultado.read_bytes() == b"RIFF-download"


class TestChamarMusicgen:
    @pytest.mark.asyncio
    async def test_api_mockada_retorna_caminho(self, service: MusicGenService) -> None:
        wav_bytes = b"RIFFfake-wav"
        mock_response = httpx.Response(
            200,
            content=wav_bytes,
            headers={"content-type": "audio/wav"},
            request=httpx.Request("POST", "http://musicgen.test/generate-from-text"),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        service._http_client = mock_client

        destino = service.audio_dir / "livro" / "partes" / "Trilha.wav"
        resultado = await service._chamar_musicgen("cinematic ambient", destino)

        assert resultado == destino
        assert destino.read_bytes() == wav_bytes

    @pytest.mark.asyncio
    async def test_api_indisponivel_retry_3x(self, service: MusicGenService) -> None:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("conexão recusada", request=MagicMock())
        )
        service._http_client = mock_client

        destino = service.audio_dir / "Trilha.wav"
        with patch("app.services.musicgen.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(MusicGenAPIError, match="3 tentativas"):
                await service._chamar_musicgen("prompt", destino)

        assert mock_client.post.await_count == 3


class TestGerarTrilha:
    @pytest.mark.asyncio
    async def test_basico_retorna_vazio(self, service: MusicGenService) -> None:
        caminho = await service.gerar_trilha("texto", "basico")
        assert caminho == ""
        service.ia_analyzer.gerar_prompt_atmosferico.assert_not_called()

    @pytest.mark.asyncio
    async def test_pipeline_completo_mockado(self, service: MusicGenService) -> None:
        service.ia_analyzer.gerar_prompt_atmosferico = AsyncMock(
            return_value="cinematic suspense, slow strings"
        )
        wav_response = httpx.Response(
            200,
            content=b"RIFF-trilha",
            headers={"content-type": "audio/wav"},
            request=httpx.Request("POST", "http://musicgen.test/generate-from-text"),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=wav_response)
        service._http_client = mock_client

        caminho = await service.gerar_trilha(
            "Noite escura na montanha.",
            "avancado",
            0,
            120,
            nome_livro="Meu Livro",
        )

        assert caminho.endswith("Trilha.wav")
        assert Path(caminho).exists()
        assert Path(caminho).read_bytes() == b"RIFF-trilha"


class TestGerarTrilhasLivro:
    @pytest.mark.asyncio
    async def test_duracao_maior_300_gera_por_pagina(self, service: MusicGenService) -> None:
        service.ia_analyzer.gerar_prompt_atmosferico = AsyncMock(
            return_value="ambient orchestral"
        )
        wav_response = httpx.Response(
            200,
            content=b"WAV",
            headers={"content-type": "audio/wav"},
            request=httpx.Request("POST", "http://musicgen.test/generate-from-text"),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=wav_response)
        service._http_client = mock_client

        paginas = [
            PaginaExcerto(1, "Página um.", 0, 200),
            PaginaExcerto(2, "Página dois.", 200, 450),
        ]
        caminhos = await service.gerar_trilhas_livro(
            paginas,
            "profissional",
            duracao_total=450,
            nome_livro="Livro Longo",
        )

        assert len(caminhos) == 2
        assert "Trilha_Pag_1" in caminhos[0]
        assert "Trilha_Pag_2" in caminhos[1]
        assert mock_client.post.await_count == 2

    @pytest.mark.asyncio
    async def test_duracao_menor_300_gera_trilha_unica(self, service: MusicGenService) -> None:
        service.ia_analyzer.gerar_prompt_atmosferico = AsyncMock(
            return_value="warm acoustic guitar"
        )
        wav_response = httpx.Response(
            200,
            content=b"WAV",
            headers={"content-type": "audio/wav"},
            request=httpx.Request("POST", "http://musicgen.test/generate-from-text"),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=wav_response)
        service._http_client = mock_client

        paginas = [
            PaginaExcerto(1, "Início.", 0, 120),
            PaginaExcerto(2, "Fim.", 120, 250),
        ]
        caminhos = await service.gerar_trilhas_livro(
            paginas,
            "avancado",
            duracao_total=250,
            nome_livro="Livro Curto",
        )

        assert len(caminhos) == 1
        assert caminhos[0].endswith("Trilha.wav")
        assert mock_client.post.await_count == 1

    @pytest.mark.asyncio
    async def test_registra_arquivo_no_banco(
        self,
        service: MusicGenService,
        db_session,
    ) -> None:
        from sqlalchemy import select

        from app.models.arquivo import Arquivo
        from app.models.livro import Livro
        from app.models.usuario import Usuario
        from app.services.auth_service import hash_password

        usuario = Usuario(login="mg_user", senha_hash=hash_password("senha123"))
        db_session.add(usuario)
        await db_session.flush()

        livro = Livro(
            titulo="Livro MG",
            nome_arquivo="livro.pdf",
            tipo_documento="pdf",
            nivel_producao="avancado",
            status="processando",
            usuario_id=usuario.id,
        )
        db_session.add(livro)
        await db_session.flush()

        service.ia_analyzer.gerar_prompt_atmosferico = AsyncMock(
            return_value="soft piano ambient"
        )
        wav_response = httpx.Response(
            200,
            content=b"RIFF",
            headers={"content-type": "audio/wav"},
            request=httpx.Request("POST", "http://musicgen.test/generate-from-text"),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=wav_response)
        service._http_client = mock_client

        caminho = await service.gerar_trilha(
            "Trecho narrativo.",
            "avancado",
            livro_id=livro.id,
            db=db_session,
            nome_livro="Livro MG",
        )

        result = await db_session.execute(
            select(Arquivo).where(Arquivo.livro_id == livro.id)
        )
        arquivo = result.scalar_one()
        assert arquivo.tipo == "trilha"
        assert arquivo.caminho == caminho


class TestCaminhoSaida:
    def test_trilha_unica_e_por_pagina(self, service: MusicGenService) -> None:
        unica = service._caminho_saida("Meu Livro")
        pagina = service._caminho_saida("Meu Livro", numero_pagina=3)
        assert unica.name == "Trilha.wav"
        assert pagina.name == "Trilha_Pag_3.wav"


class TestFromDb:
    @pytest.mark.asyncio
    async def test_from_db_sem_analyzer_config(
        self, db_session, db_factory
    ) -> None:
        from tests.factories import ApiConfigFactory, persist

        await persist(
            db_session,
            ApiConfigFactory,
            tipo="musicgen",
            modo="local",
            url="http://musicgen:8002",
            token=None,
        )
        mock_analyzer = AsyncMock(spec=IAAnalyzer)
        with patch.object(
            IAAnalyzer,
            "from_db",
            new_callable=AsyncMock,
            return_value=mock_analyzer,
        ):
            svc = await MusicGenService.from_db(db_session)
        assert svc.api_url == "http://musicgen:8002"


class TestContextManager:
    @pytest.mark.asyncio
    async def test_aclose_fecha_client_e_analyzer(self, service: MusicGenService) -> None:
        service._http_client = AsyncMock()
        service._http_client.aclose = AsyncMock()
        service._owns_client = True
        service._owns_analyzer = True
        service.ia_analyzer.aclose = AsyncMock()
        await service.aclose()
        service.ia_analyzer.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_async_context_manager(self, service: MusicGenService) -> None:
        async with service as svc:
            assert svc is service
