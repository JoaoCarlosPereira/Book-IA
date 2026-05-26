"""Pydantic schema validation tests for IA schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.ia import CharacterProfile, IAProvider, LLMEndpointConfig


class TestCharacterProfile:
    def test_strip_nome(self) -> None:
        profile = CharacterProfile(nome="  João  ", genero="masculino", idade="adulto")
        assert profile.nome == "João"

    def test_defaults_genero_idade(self) -> None:
        profile = CharacterProfile(nome="Narrador")
        assert profile.genero == "neutro"
        assert profile.idade == "adulto"

    def test_genero_invalido(self) -> None:
        with pytest.raises(ValidationError):
            CharacterProfile(nome="X", genero="outro", idade="adulto")  # type: ignore[arg-type]

    def test_idade_invalida(self) -> None:
        with pytest.raises(ValidationError):
            CharacterProfile(nome="X", genero="neutro", idade="teen")  # type: ignore[arg-type]


class TestLLMEndpointConfig:
    def test_config_frozen(self) -> None:
        cfg = LLMEndpointConfig(
            url="http://localhost:11434",
            modo=IAProvider.LOCAL,
            modelo="gemma3",
        )
        with pytest.raises(ValidationError):
            cfg.url = "http://outro"  # type: ignore[misc]

    def test_modo_cloud(self) -> None:
        cfg = LLMEndpointConfig(
            url="https://generativelanguage.googleapis.com",
            modo=IAProvider.CLOUD,
            token="key",
        )
        assert cfg.modo == IAProvider.CLOUD
        assert cfg.token == "key"
