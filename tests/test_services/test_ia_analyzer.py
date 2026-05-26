"""Unit tests for IAAnalyzer (parsing, retry, fallback)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.schemas.ia import CharacterProfile, IAProvider, LLMEndpointConfig
from app.services.ia_analyzer import (
    CLOUD_BACKOFF,
    CLOUD_RETRIES,
    IAAnalyzer,
    IAAnalyzerError,
    LLMConnectionError,
    LLMUnavailableError,
    LOCAL_BACKOFF,
    LOCAL_RETRIES,
    RateLimitError,
)

CLOUD_CONFIG = LLMEndpointConfig(
    url="https://generativelanguage.googleapis.com",
    modo=IAProvider.CLOUD,
    token="test-key",
    modelo="gemini-2.0-flash",
)
LOCAL_CONFIG = LLMEndpointConfig(
    url="http://ollama.local:11434",
    modo=IAProvider.LOCAL,
    modelo="gemma3:27b-it-qat",
)


def _gemini_response(text: str) -> dict[str, Any]:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": text}],
                },
            },
        ],
    }


def _ollama_response(text: str) -> dict[str, Any]:
    return {"message": {"role": "assistant", "content": text}}


@pytest.fixture()
def analyzer() -> IAAnalyzer:
    return IAAnalyzer(cloud_config=CLOUD_CONFIG, local_config=LOCAL_CONFIG)


class TestParseResposta:
    def test_parse_json_invalido_faz_fallback_para_linhas(self, analyzer: IAAnalyzer) -> None:
        raw = "not json at all\njoão|male|adult"
        result = analyzer._parse_resposta(raw)
        assert len(result) == 1
        assert result[0].nome == "joão"

    def test_parse_json_invalido_sem_linhas_retorna_vazio(self, analyzer: IAAnalyzer) -> None:
        assert analyzer._parse_resposta("{invalid json") == []

    def test_parse_json_array(self, analyzer: IAAnalyzer) -> None:
        raw = json.dumps(
            [
                {"nome": "João", "genero": "male", "idade": "Adult"},
                {"nome": "Maria", "genero": "female", "idade": "Child"},
            ]
        )
        result = analyzer._parse_resposta(raw)
        assert len(result) == 2
        assert result[0].nome == "joão"
        assert result[0].genero == "masculino"
        assert result[0].idade == "adulto"
        assert result[1].genero == "feminino"
        assert result[1].idade == "crianca"

    def test_parse_json_fenced(self, analyzer: IAAnalyzer) -> None:
        raw = '```json\n[{"nome": "Ana", "genero": "feminino", "idade": "idoso"}]\n```'
        result = analyzer._parse_resposta(raw)
        assert len(result) == 1
        assert result[0].nome == "ana"
        assert result[0].idade == "idoso"

    def test_parse_linha_nome_genero_idade(self, analyzer: IAAnalyzer) -> None:
        raw = "João|male|adult\nMaria|female|child"
        result = analyzer._parse_resposta(raw)
        assert result[0].nome == "joão"
        assert result[0].genero == "masculino"
        assert result[0].idade == "adulto"
        assert result[1].idade == "crianca"

    def test_parse_linha_nome_fala(self, analyzer: IAAnalyzer) -> None:
        raw = "joão|Olá, como vai?\nnarrator|Era uma vez."
        result = analyzer._parse_resposta(raw)
        assert len(result) == 2
        assert result[0].nome == "joão"
        assert result[1].nome == "narrator"

    def test_parse_perfil_genero_idade(self, analyzer: IAAnalyzer) -> None:
        genero, idade = analyzer._parse_genero_idade_linha("Male|Adult")
        assert genero == "Male"
        assert idade == "Adult"


class TestChamarLlmCloud:
    @pytest.mark.asyncio()
    async def test_cloud_success(self, analyzer: IAAnalyzer) -> None:
        mock_response = httpx.Response(
            200,
            json=_gemini_response("joão|Olá"),
            request=httpx.Request("POST", "https://example.com"),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        analyzer._client = mock_client

        result = await analyzer._chamar_llm_cloud("prompt", "texto")
        assert result == "joão|Olá"
        mock_client.post.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_cloud_rate_limit_raises(self, analyzer: IAAnalyzer) -> None:
        mock_response = httpx.Response(
            429,
            text='{"error": "quota exceeded"}',
            request=httpx.Request("POST", "https://example.com"),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        analyzer._client = mock_client

        with pytest.raises(RateLimitError):
            await analyzer._chamar_llm_cloud("prompt", "texto")

    @pytest.mark.asyncio()
    async def test_cloud_connection_error(self, analyzer: IAAnalyzer) -> None:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        analyzer._client = mock_client

        with pytest.raises(LLMConnectionError):
            await analyzer._chamar_llm_cloud("prompt", "texto")

    @pytest.mark.asyncio()
    async def test_cloud_http_500_raises_connection_error(self, analyzer: IAAnalyzer) -> None:
        mock_response = httpx.Response(
            500,
            text="internal server error",
            request=httpx.Request("POST", "https://example.com"),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        analyzer._client = mock_client

        with pytest.raises(LLMConnectionError, match="HTTP 500"):
            await analyzer._chamar_llm_cloud("prompt", "texto")

    @pytest.mark.asyncio()
    async def test_cloud_uses_60s_timeout(self, analyzer: IAAnalyzer) -> None:
        from app.services.ia_analyzer import CLOUD_TIMEOUT

        mock_response = httpx.Response(
            200,
            json=_gemini_response("ok"),
            request=httpx.Request("POST", "https://example.com"),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        analyzer._client = mock_client

        await analyzer._chamar_llm_cloud("prompt", "texto")
        _, kwargs = mock_client.post.await_args
        assert kwargs["timeout"] == CLOUD_TIMEOUT
        assert CLOUD_TIMEOUT == 60.0


class TestChamarLlmLocal:
    @pytest.mark.asyncio()
    async def test_local_uses_120s_timeout(self, analyzer: IAAnalyzer) -> None:
        from app.services.ia_analyzer import LOCAL_TIMEOUT

        mock_response = httpx.Response(
            200,
            json=_ollama_response("resposta"),
            request=httpx.Request("POST", "http://ollama.local/api/chat"),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        analyzer._client = mock_client

        await analyzer._chamar_llm_local("prompt", "texto")
        _, kwargs = mock_client.post.await_args
        assert kwargs["timeout"] == LOCAL_TIMEOUT
        assert LOCAL_TIMEOUT == 120.0


class TestRetry:
    @pytest.mark.asyncio()
    async def test_cloud_retry_three_times(self, analyzer: IAAnalyzer) -> None:
        sleep_mock = AsyncMock()
        call_count = 0

        async def failing_cloud(prompt: str, conteudo: str) -> str:
            nonlocal call_count
            call_count += 1
            raise LLMConnectionError("falha")

        with (
            patch.object(analyzer, "_chamar_llm_cloud", side_effect=failing_cloud),
            patch("app.services.ia_analyzer.asyncio.sleep", sleep_mock),
            pytest.raises(LLMConnectionError),
        ):
            await analyzer._chamar_com_retry(
                analyzer._chamar_llm_cloud,
                "p",
                "c",
                retries=CLOUD_RETRIES,
                backoff=CLOUD_BACKOFF,
            )

        assert call_count == CLOUD_RETRIES
        assert sleep_mock.await_count == CLOUD_RETRIES - 1
        sleep_mock.assert_any_await(CLOUD_BACKOFF[0])
        sleep_mock.assert_any_await(CLOUD_BACKOFF[1])

    @pytest.mark.asyncio()
    async def test_local_retry_two_times(self, analyzer: IAAnalyzer) -> None:
        sleep_mock = AsyncMock()
        call_count = 0

        async def failing_local(prompt: str, conteudo: str) -> str:
            nonlocal call_count
            call_count += 1
            raise LLMConnectionError("falha local")

        with (
            patch.object(analyzer, "_chamar_llm_local", side_effect=failing_local),
            patch("app.services.ia_analyzer.asyncio.sleep", sleep_mock),
            pytest.raises(LLMConnectionError),
        ):
            await analyzer._chamar_com_retry(
                analyzer._chamar_llm_local,
                "p",
                "c",
                retries=LOCAL_RETRIES,
                backoff=LOCAL_BACKOFF,
            )

        assert call_count == LOCAL_RETRIES
        assert sleep_mock.await_count == LOCAL_RETRIES - 1


class TestFallback:
    @pytest.mark.asyncio()
    async def test_fallback_cloud_to_local_on_rate_limit(self, analyzer: IAAnalyzer) -> None:
        async def retry_side_effect(caller, prompt, conteudo, *, retries, backoff):
            if caller == analyzer._chamar_llm_cloud:
                raise RateLimitError("quota")
            return "resposta local"

        with patch.object(analyzer, "_chamar_com_retry", side_effect=retry_side_effect):
            result = await analyzer._chamar_llm("prompt", "texto")

        assert result == "resposta local"

    @pytest.mark.asyncio()
    async def test_fallback_on_connection_error(self, analyzer: IAAnalyzer) -> None:
        async def retry_side_effect(caller, prompt, conteudo, *, retries, backoff):
            if caller == analyzer._chamar_llm_cloud:
                raise LLMConnectionError("timeout")
            return "ok local"

        with patch.object(analyzer, "_chamar_com_retry", side_effect=retry_side_effect):
            result = await analyzer._chamar_llm("prompt", "texto")
        assert result == "ok local"

    @pytest.mark.asyncio()
    async def test_local_failure_no_extra_fallback(self, analyzer: IAAnalyzer) -> None:
        cloud_only = IAAnalyzer(cloud_config=None, local_config=LOCAL_CONFIG)

        async def failing_local(prompt: str, conteudo: str) -> str:
            raise LLMConnectionError("local down")

        with (
            patch.object(cloud_only, "_chamar_llm_local", side_effect=failing_local),
            patch.object(
                cloud_only,
                "_chamar_com_retry",
                side_effect=LLMConnectionError("local down"),
            ),
            pytest.raises(LLMUnavailableError) as exc_info,
        ):
            await cloud_only._chamar_llm("prompt", "texto")

        assert "local" in str(exc_info.value).lower()

    @pytest.mark.asyncio()
    async def test_both_providers_fail_descriptive_error(self, analyzer: IAAnalyzer) -> None:
        async def retry_side_effect(caller, prompt, conteudo, *, retries, backoff):
            if caller == analyzer._chamar_llm_cloud:
                raise RateLimitError("cloud quota")
            raise LLMConnectionError("local offline")

        with (
            patch.object(analyzer, "_chamar_com_retry", side_effect=retry_side_effect),
            pytest.raises(LLMUnavailableError) as exc_info,
        ):
            await analyzer._chamar_llm("prompt", "texto")

        err = exc_info.value
        assert err.cloud_error is not None
        assert err.local_error is not None
        assert "cloud" in str(err).lower()
        assert "local" in str(err).lower()


class TestExtrairPersonagens:
    @pytest.mark.asyncio()
    async def test_extrair_com_cloud_mock(self, analyzer: IAAnalyzer) -> None:
        llm_response = "joão|Olá!\nmaria|Oi!\nnarrator|Era uma vez."
        with patch.object(analyzer, "_chamar_llm", return_value=llm_response):
            result = await analyzer.extrair_personagens("texto do livro")

        nomes = {p.nome for p in result}
        assert nomes == {"joão", "maria", "narrator"}

    @pytest.mark.asyncio()
    async def test_extrair_no_characters(self, analyzer: IAAnalyzer) -> None:
        with patch.object(analyzer, "_chamar_llm", return_value="no characters"):
            result = await analyzer.extrair_personagens("texto")
        assert result == []


class TestNormalizarEDefinirPerfil:
    @pytest.mark.asyncio()
    async def test_normalizar_nomes(self, analyzer: IAAnalyzer) -> None:
        entrada = [
            CharacterProfile(nome="joao", genero="neutro", idade="adulto"),
            CharacterProfile(nome="maria", genero="neutro", idade="adulto"),
        ]
        resposta = "0|João|male\n1|Maria|female"
        with patch.object(analyzer, "_chamar_llm", return_value=resposta):
            result = await analyzer.normalizar_nomes(entrada)

        assert result[0].nome == "joão"
        assert result[0].genero == "masculino"
        assert result[1].genero == "feminino"

    @pytest.mark.asyncio()
    async def test_definir_perfil(self, analyzer: IAAnalyzer) -> None:
        with patch.object(analyzer, "_chamar_llm", return_value="Male|Adult"):
            profile = await analyzer.definir_perfil("falas do personagem", "João")

        assert profile.nome == "joão"
        assert profile.genero == "masculino"
        assert profile.idade == "adulto"


class TestIntegrationMockTransport:
    @pytest.mark.asyncio()
    async def test_full_flow_cloud_mock_transport(self) -> None:
        calls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(str(request.url))
            if "generativelanguage" in str(request.url):
                return httpx.Response(200, json=_gemini_response("pedro|Olá"))
            return httpx.Response(200, json=_ollama_response("fallback"))

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            analyzer = IAAnalyzer(
                cloud_config=CLOUD_CONFIG,
                local_config=LOCAL_CONFIG,
                client=client,
            )
            result = await analyzer.extrair_personagens("capítulo um")

        assert any("generativelanguage" in url for url in calls)
        assert any(p.nome == "pedro" for p in result)

    @pytest.mark.asyncio()
    async def test_full_flow_fallback_to_local(self) -> None:
        call_modes: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "generativelanguage" in url:
                call_modes.append("cloud")
                return httpx.Response(429, text='{"error": "quota exceeded"}')
            call_modes.append("local")
            return httpx.Response(200, json=_ollama_response("ana|Oi"))

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            analyzer = IAAnalyzer(
                cloud_config=CLOUD_CONFIG,
                local_config=LOCAL_CONFIG,
                client=client,
            )
            with patch("app.services.ia_analyzer.asyncio.sleep", AsyncMock()):
                result = await analyzer.extrair_personagens("texto")

        assert "cloud" in call_modes
        assert "local" in call_modes
        assert any(p.nome == "ana" for p in result)


class TestHelpers:
    def test_formatar_tempo(self) -> None:
        from app.services.ia_analyzer import _formatar_tempo

        assert _formatar_tempo(3661) == "01:01:01"

    def test_extrair_prompt_ingles_com_aspas(self) -> None:
        from app.services.ia_analyzer import _extrair_prompt_ingles

        assert "ambient" in _extrair_prompt_ingles('"soft ambient piano"')

    def test_extrair_prompt_ingles_vazio_levanta(self) -> None:
        from app.services.ia_analyzer import IAAnalyzerError, _extrair_prompt_ingles

        with pytest.raises(IAAnalyzerError):
            _extrair_prompt_ingles("   ")

    def test_build_cloud_url_com_generate_content(self) -> None:
        url = IAAnalyzer._build_cloud_url(
            "https://generativelanguage.googleapis.com/v1beta/models/x:generateContent?key=abc",
            "model",
            "extra",
        )
        assert "generateContent" in url
        assert "key=abc" in url

    def test_build_local_url_com_path_customizado(self) -> None:
        url = IAAnalyzer._build_local_url("http://host/custom/api/chat")
        assert url.endswith("/api/chat")

    def test_parse_json_com_chave_personagens(self, analyzer: IAAnalyzer) -> None:
        raw = '{"personagens": [{"nome": "Pedro", "genero": "male", "idade": "adult"}]}'
        result = analyzer._parse_resposta(raw)
        assert result[0].nome == "pedro"

    def test_parse_linha_com_id_numerico(self, analyzer: IAAnalyzer) -> None:
        profile = analyzer._parse_linha("0|João|male")
        assert profile is not None
        assert profile.nome == "joão"

    def test_merge_normalizacao(self, analyzer: IAAnalyzer) -> None:
        entrada = [CharacterProfile(nome="joao", genero="neutro", idade="adulto")]
        resposta = "0|João|male\n1|Maria|female"
        merged = analyzer._merge_normalizacao(entrada, resposta)
        assert merged[0].nome == "joão"
        assert merged[0].genero == "masculino"


class TestGerarPromptAtmosferico:
    @pytest.mark.asyncio
    async def test_gerar_prompt_com_faixa_tempo(self, analyzer: IAAnalyzer) -> None:
        with patch.object(analyzer, "_chamar_llm", return_value='"dark orchestral suspense"'):
            prompt = await analyzer.gerar_prompt_atmosferico("trecho", 60, 120)
        assert "orchestral" in prompt

    @pytest.mark.asyncio
    async def test_normalizar_lista_vazia(self, analyzer: IAAnalyzer) -> None:
        assert await analyzer.normalizar_nomes([]) == []


class TestContextManager:
    @pytest.mark.asyncio
    async def test_aclose_owned_client(self) -> None:
        analyzer = IAAnalyzer(cloud_config=CLOUD_CONFIG)
        await analyzer._get_client()
        await analyzer.aclose()
        assert analyzer._client is None

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        async with IAAnalyzer(cloud_config=CLOUD_CONFIG) as analyzer:
            assert analyzer._cloud is not None


class TestExtrairPersonagensDedup:
    @pytest.mark.asyncio
    async def test_remove_nomes_duplicados(self, analyzer: IAAnalyzer) -> None:
        raw = "joão|Olá\njoão|Oi de novo"
        with patch.object(analyzer, "_chamar_llm", return_value=raw):
            result = await analyzer.extrair_personagens("texto")
        assert len(result) == 1


class TestChamarLlmErrors:
    @pytest.mark.asyncio
    async def test_cloud_400_raises_ia_error(self, analyzer: IAAnalyzer) -> None:
        mock_response = httpx.Response(
            400,
            text="bad request",
            request=httpx.Request("POST", "https://example.com"),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        analyzer._client = mock_client

        with pytest.raises(IAAnalyzerError) as exc_info:
            await analyzer._chamar_llm_cloud("prompt", "texto")
        assert "400" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cloud_json_invalido(self, analyzer: IAAnalyzer) -> None:
        mock_response = httpx.Response(
            200,
            text="not json",
            request=httpx.Request("POST", "https://example.com"),
        )
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        analyzer._client = mock_client

        with pytest.raises(IAAnalyzerError) as exc_info:
            await analyzer._chamar_llm_cloud("prompt", "texto")
        assert "JSON" in str(exc_info.value)
