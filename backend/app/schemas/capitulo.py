"""Pydantic schemas for chapters."""

from pydantic import BaseModel, ConfigDict


class CapituloResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: int
    titulo: str
    pagina_inicio: int | None = None
    pagina_fim: int | None = None
    caminho_audio: str | None = None
    duracao_estimada: int | None = None


class CapituloLista(BaseModel):
    items: list[CapituloResumo]
    total: int
