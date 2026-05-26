"""Schemas for book task queue API."""

from pydantic import BaseModel, Field


class ReorderItem(BaseModel):
    task_id: int
    prioridade: int = Field(ge=1, le=10)


class ReorderRequest(BaseModel):
    items: list[ReorderItem]


class TaskStatusResponse(BaseModel):
    task_id: int
    livro_id: int
    status: str
    prioridade: int
    progresso: int
