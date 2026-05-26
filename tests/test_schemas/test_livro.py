"""Pydantic schema validation tests for livro schemas."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.livro import (
    EXTENSION_TO_DOC_TYPE,
    VALID_EXTENSIONS,
    LivroDetalheResponse,
    LivroListItem,
    LivroReordenarRequest,
    LivroUploadResponse,
    PersonagemResumo,
)


class TestLivroUploadResponse:
    def test_valid_upload_response(self) -> None:
        model = LivroUploadResponse(id=1, status="pendente")
        assert model.id == 1
        assert model.status == "pendente"

    def test_missing_fields_raise(self) -> None:
        with pytest.raises(ValidationError):
            LivroUploadResponse(id=1)  # type: ignore[call-arg]


class TestLivroListItem:
    def test_from_attributes(self) -> None:
        now = datetime(2026, 5, 26, 12, 0, 0)

        class Row:
            id = 10
            titulo = "Meu Livro"
            nome_arquivo = "livro.pdf"
            tipo_documento = "pdf"
            nivel_producao = "basico"
            status = "processando"
            progresso = 50
            criado_em = now
            atualizado_em = now

        item = LivroListItem.model_validate(Row())
        assert item.titulo == "Meu Livro"
        assert item.progresso == 50


class TestLivroReordenarRequest:
    def test_prioridade_valida(self) -> None:
        req = LivroReordenarRequest(prioridade=5)
        assert req.prioridade == 5

    def test_prioridade_fora_do_intervalo(self) -> None:
        with pytest.raises(ValidationError):
            LivroReordenarRequest(prioridade=0)
        with pytest.raises(ValidationError):
            LivroReordenarRequest(prioridade=11)


class TestExtensionMapping:
    def test_valid_extensions(self) -> None:
        assert ".pdf" in VALID_EXTENSIONS
        assert EXTENSION_TO_DOC_TYPE[".epub"] == "epub"


class TestPersonagemResumo:
    def test_defaults(self) -> None:
        p = PersonagemResumo(id=1, nome="João")
        assert p.genero is None
        assert p.is_narrador is False
        assert p.voz_id is None


class TestLivroDetalheResponse:
    def test_personagens_default_lista_vazia(self) -> None:
        now = datetime(2026, 5, 26, 12, 0, 0)
        detalhe = LivroDetalheResponse(
            id=1,
            titulo="T",
            nome_arquivo="t.pdf",
            tipo_documento="pdf",
            nivel_producao="basico",
            status="pendente",
            progresso=0,
            criado_em=now,
            atualizado_em=now,
        )
        assert detalhe.personagens == []
