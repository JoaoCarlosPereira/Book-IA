"""Pydantic schemas for livros API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DocumentType = Literal["pdf", "epub", "txt"]
NivelProducao = Literal["basico", "avancado", "profissional"]

VALID_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".epub", ".txt"})
EXTENSION_TO_DOC_TYPE: dict[str, DocumentType] = {
    ".pdf": "pdf",
    ".epub": "epub",
    ".txt": "txt",
}


class LivroUploadResponse(BaseModel):
    id: int
    status: str


class LivroListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    nome_arquivo: str
    tipo_documento: str
    nivel_producao: str
    status: str
    progresso: int
    criado_em: datetime
    atualizado_em: datetime


class LivroListResponse(BaseModel):
    items: list[LivroListItem]
    total: int
    pagina: int
    por_pagina: int


class PersonagemResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    genero: str | None = None
    idade: str | None = None
    is_narrador: bool = False
    voz_id: int | None = None


class LivroDetalheResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    nome_arquivo: str
    tipo_documento: str
    nivel_producao: str
    status: str
    progresso: int
    etapa: str | None = None
    task_status: str | None = None
    prioridade: int | None = None
    erro: str | None = None
    criado_em: datetime
    atualizado_em: datetime
    personagens: list[PersonagemResumo] = Field(default_factory=list)
    capitulos: list[dict] = Field(default_factory=list)


class LivroProgresso(BaseModel):
    progresso: int
    etapa: str
    status: str


class LivroStatusResponse(BaseModel):
    status: str


class LivroPrioridadeResponse(BaseModel):
    prioridade: int


class LivroReordenarRequest(BaseModel):
    prioridade: int = Field(ge=1, le=10)
