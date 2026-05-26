"""Add celery_task_id to book_task.

Revision ID: 002
Revises: 001
Create Date: 2026-05-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "book_task",
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("book_task", "celery_task_id")
