"""Pydantic schemas for IA analysis (character profiles, LLM config)."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

GeneroLiteral = Literal["masculino", "feminino", "neutro"]
IdadeLiteral = Literal["crianca", "adulto", "idoso"]


class IAProvider(str, Enum):
    CLOUD = "cloud"
    LOCAL = "local"


class CharacterProfile(BaseModel):
    nome: str
    genero: GeneroLiteral = "neutro"
    idade: IdadeLiteral = "adulto"

    @field_validator("nome", mode="before")
    @classmethod
    def strip_nome(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value


class LLMEndpointConfig(BaseModel):
    """Runtime LLM endpoint loaded from api_config."""

    url: str
    modo: IAProvider
    token: str | None = None
    modelo: str | None = None

    model_config = {"frozen": True}
