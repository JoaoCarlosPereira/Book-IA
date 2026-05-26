"""Smoke tests for factory_boy model factories."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests import factories


@pytest.mark.asyncio
async def test_usuario_factory_persist(db_session: AsyncSession, db_factory: None) -> None:
    usuario = await factories.persist(db_session, factories.UsuarioFactory)
    assert usuario.id is not None
    assert usuario.login.startswith("usuario")


@pytest.mark.asyncio
async def test_livro_factory_with_relations(
    db_session: AsyncSession, db_factory: None
) -> None:
    usuario = await factories.persist(db_session, factories.UsuarioFactory)
    livro = factories.LivroFactory.build(usuario_id=usuario.id)
    db_session.add(livro)
    await db_session.flush()
    assert livro.usuario_id == usuario.id
