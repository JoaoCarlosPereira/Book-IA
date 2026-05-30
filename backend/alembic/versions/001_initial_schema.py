"""Initial schema — all Book-IA tables.

Revision ID: 001
Revises:
Create Date: 2026-05-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuario",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("login", sa.String(length=100), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column("perfil", sa.String(length=20), server_default="usuario", nullable=False),
        sa.Column("criado_em", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("atualizado_em", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("login"),
    )
    op.create_table(
        "voz",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("genero", sa.String(length=20), nullable=False),
        sa.Column("idade", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "api_config",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("modo", sa.String(length=10), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("token", sa.String(length=500), nullable=True),
        sa.Column("modelo", sa.String(length=200), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("criado_em", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("atualizado_em", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "livro",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("titulo", sa.String(length=500), nullable=False),
        sa.Column("nome_arquivo", sa.String(length=500), nullable=False),
        sa.Column("tipo_documento", sa.String(length=10), nullable=False),
        sa.Column("nivel_producao", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pendente", nullable=False),
        sa.Column("progresso", sa.Integer(), server_default="0", nullable=False),
        sa.Column("caminho_pdf", sa.String(length=1000), nullable=True),
        sa.Column("caminho_audio", sa.String(length=1000), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "pagina",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("livro_id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["livro_id"], ["livro.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "arquivo",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("livro_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("caminho", sa.String(length=1000), nullable=False),
        sa.Column("tamanho_bytes", sa.BigInteger(), nullable=True),
        sa.Column("criado_em", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["livro_id"], ["livro.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "personagem",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("livro_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("genero", sa.String(length=20), nullable=True),
        sa.Column("idade", sa.String(length=20), nullable=True),
        sa.Column("voz_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["livro_id"], ["livro.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["voz_id"], ["voz.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "book_task",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("livro_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("prioridade", sa.Integer(), server_default="5", nullable=True),
        sa.Column("progresso", sa.Integer(), server_default="0", nullable=True),
        sa.Column("etapa_atual", sa.String(length=100), nullable=True),
        sa.Column("erro", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("atualizado_em", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["livro_id"], ["livro.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "falas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("livro_id", sa.Integer(), nullable=False),
        sa.Column("pagina_id", sa.Integer(), nullable=False),
        sa.Column("personagem_id", sa.Integer(), nullable=True),
        sa.Column("arquivo_id", sa.Integer(), nullable=True),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["arquivo_id"], ["arquivo.id"]),
        sa.ForeignKeyConstraint(["livro_id"], ["livro.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pagina_id"], ["pagina.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["personagem_id"], ["personagem.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "book_review",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("livro_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("personagem_id", sa.Integer(), nullable=True),
        sa.Column("acao", sa.String(length=20), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["livro_id"], ["livro.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["personagem_id"], ["personagem.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "capitulo",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("livro_id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=500), nullable=False),
        sa.Column("pagina_inicio", sa.Integer(), nullable=True),
        sa.Column("pagina_fim", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["livro_id"], ["livro.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("capitulo")
    op.drop_table("book_review")
    op.drop_table("falas")
    op.drop_table("book_task")
    op.drop_table("personagem")
    op.drop_table("arquivo")
    op.drop_table("pagina")
    op.drop_table("livro")
    op.drop_table("api_config")
    op.drop_table("voz")
    op.drop_table("usuario")
