"""Pydantic schemas for character review (Fase 2)."""

from pydantic import BaseModel, ConfigDict, Field


class FalaResumo(BaseModel):
    """A single dialogue line with page context."""
    id: int
    texto: str
    pagina_numero: int

    model_config = ConfigDict(from_attributes=True)


class PersonagemComFalasResponse(BaseModel):
    """Character with their dialogues for review."""
    id: int
    nome: str
    nome_original: str | None = None
    genero: str | None = None
    idade: str | None = None
    is_narrador: bool = False
    voz_id: int | None = None
    falas: list[FalaResumo] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PersonagemUpdateRequest(BaseModel):
    """Request to update a character during review."""
    nome: str = Field(min_length=1, max_length=200)
    genero: str = Field(description="masculino, feminino, neutro")
    idade: str = Field(description="crianca, adulto, idoso")
    voz_id: int | None = None
