"""Pydantic schema validation tests for api_config schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.api_config import (
    ApiConfigCreate,
    ApiConfigTestResponse,
    ApiConfigUpdate,
)


class TestApiConfigCreate:
    def test_normaliza_tipo_e_modo(self) -> None:
        cfg = ApiConfigCreate(
            tipo="LLM",
            modo="CLOUD",
            url="https://api.example.com",
        )
        assert cfg.tipo == "llm"
        assert cfg.modo == "cloud"

    def test_url_obrigatoria(self) -> None:
        with pytest.raises(ValidationError):
            ApiConfigCreate(tipo="tts", modo="local", url="")

    def test_token_opcional(self) -> None:
        cfg = ApiConfigCreate(tipo="musicgen", modo="local", url="http://localhost:8002")
        assert cfg.token is None
        assert cfg.ativo is True


class TestApiConfigUpdate:
    def test_campos_parciais(self) -> None:
        upd = ApiConfigUpdate(url="http://novo.host")
        assert upd.tipo is None
        assert upd.url == "http://novo.host"

    def test_normaliza_modo(self) -> None:
        upd = ApiConfigUpdate(modo=" Local ")
        assert upd.modo == "local"


class TestApiConfigTestResponse:
    def test_resposta_conectado(self) -> None:
        resp = ApiConfigTestResponse(conectado=True, latencia_ms=120)
        assert resp.conectado is True
        assert resp.erro is None

    def test_resposta_erro(self) -> None:
        resp = ApiConfigTestResponse(conectado=False, erro="timeout")
        assert resp.latencia_ms is None
