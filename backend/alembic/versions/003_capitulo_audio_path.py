"""Add caminho_audio and duracao_estimada to capitulo.

Revision ID: 003
Revises: 002
Create Date: 2026-05-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "capitulo",
        sa.Column("caminho_audio", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "capitulo",
        sa.Column("duracao_estimada", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("capitulo", "duracao_estimada")
    op.drop_column("capitulo", "caminho_audio")
