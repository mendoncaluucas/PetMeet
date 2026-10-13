"""atendimento clinico

Ficha clinica do pet (fase 2, H3): cada atendimento com anamnese, diagnostico e conduta,
registrado por um veterinario. Nao ha edicao nem exclusao: o atendimento e anulado com
motivo, e a constraint exige quando, quem e por que juntos (D8). As chaves estrangeiras
sao RESTRICT: apagar um pet ou um usuario nao leva o historico clinico junto (A-09).

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-13

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "atendimentos_clinicos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pet_id", sa.Integer(), nullable=False),
        sa.Column("veterinario_id", sa.Integer(), nullable=False),
        sa.Column("data_atendimento", sa.Date(), nullable=False),
        sa.Column("anamnese", sa.String(length=5000), nullable=False),
        sa.Column("diagnostico", sa.String(length=2000), nullable=True),
        sa.Column("conduta", sa.String(length=2000), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("anulado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anulado_por_id", sa.Integer(), nullable=True),
        sa.Column("motivo_anulacao", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "(anulado_em IS NULL AND anulado_por_id IS NULL AND motivo_anulacao IS NULL)"
            " OR (anulado_em IS NOT NULL AND anulado_por_id IS NOT NULL"
            " AND motivo_anulacao IS NOT NULL)",
            name="ck_atendimentos_clinicos_anulacao_completa",
        ),
        sa.ForeignKeyConstraint(["anulado_por_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["veterinario_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_atendimentos_clinicos_pet_data",
        "atendimentos_clinicos",
        ["pet_id", "data_atendimento"],
        unique=False,
    )


def downgrade() -> None:
    # Desfazer esta migration apaga a tabela: com atendimentos gravados, seria apagar
    # historico clinico, que o N2 nao apaga nunca. So desce com a tabela vazia.
    atendimentos = op.get_bind().scalar(sa.text("SELECT count(*) FROM atendimentos_clinicos"))
    if atendimentos:
        raise RuntimeError(
            f"Ha {atendimentos} atendimento(s) na ficha clinica. Desfazer esta migration "
            "apagaria esse historico; exporte e remova os dados antes, se for mesmo o caso."
        )
    op.drop_index("ix_atendimentos_clinicos_pet_data", table_name="atendimentos_clinicos")
    op.drop_table("atendimentos_clinicos")
