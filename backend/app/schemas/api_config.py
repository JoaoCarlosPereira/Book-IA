"""Pydantic schemas for API configuration."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ApiTipo = Literal["llm", "tts", "musicgen"]
ApiModo = Literal["cloud", "local"]

VALID_TIPOS = frozenset({"llm", "tts", "musicgen"})
VALID_MODOS = frozenset({"cloud", "local"})


class ApiConfigCreate(BaseModel):
    tipo: ApiTipo
    modo: ApiModo
    url: str = Field(..., min_length=1, max_length=500)
    token: str | None = Field(default=None, max_length=500)
    modelo: str | None = Field(default=None, max_length=200)
    ativo: bool = True

    @field_validator("tipo", "modo", mode="before")
    @classmethod
    def normalize_lower(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class ApiConfigUpdate(BaseModel):
    tipo: ApiTipo | None = None
    modo: ApiModo | None = None
    url: str | None = Field(default=None, min_length=1, max_length=500)
    token: str | None = Field(default=None, max_length=500)
    modelo: str | None = Field(default=None, max_length=200)
    ativo: bool | None = None

    @field_validator("tipo", "modo", mode="before")
    @classmethod
    def normalize_lower(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class ApiConfigResponse(BaseModel):
    id: int
    tipo: str
    modo: str
    url: str
    token: str | None = None
    modelo: str | None = None
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ApiConfigTestResponse(BaseModel):
    conectado: bool
    latencia_ms: int | None = None
    erro: str | None = None
