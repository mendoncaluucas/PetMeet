"""perfil veterinario

Perfil novo da fase 2: o veterinario cuida da parte clinica e e o unico que da alta de
um tratamento medico (docs/HISTORIAS-FASE-2.md, H1 e H2).

Esta migration so acrescenta o valor ao tipo, e fica sozinha de proposito (A-04): o
Postgres nao deixa usar um valor de enum na mesma transacao que o criou, e o env.py roda
todas as migrations pendentes numa transacao so. Nenhuma migration seguinte pode usar
'veterinario'.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-13

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE perfil_usuario ADD VALUE IF NOT EXISTS 'veterinario'")


def downgrade() -> None:
    # O Postgres nao tem DROP VALUE: o valor fica no tipo, sem uso. O que nao pode ficar
    # e usuario com esse perfil -- o codigo da versao anterior nao o reconhece e o login
    # dele daria erro 500. Trocar o perfil ou inativar esses usuarios antes de voltar.
    veterinarios = op.get_bind().scalar(
        sa.text("SELECT count(*) FROM usuarios WHERE perfil::text = 'veterinario'")
    )
    if veterinarios:
        raise RuntimeError(
            f"Ha {veterinarios} usuario(s) com perfil veterinario. Troque o perfil deles "
            "antes de desfazer esta migration."
        )
