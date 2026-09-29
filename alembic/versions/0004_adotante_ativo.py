"""adotante ativo

Adotante inativo sai das listagens e nao abre processo novo. Quem tem processo de
adocao no historico nao pode ser excluido -- so inativado (DEF-13). Os cadastros
existentes entram como ativos.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-29

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "adotantes",
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("adotantes", "ativo")
