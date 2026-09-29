"""um processo de adocao ativo por pet

Indice unico parcial: um pet so pode ter um processo em analise ou aprovado por vez.
A situacao de adocao do pet deixa de ser editavel a mao e passa a ser so efeito do
processo; este indice e a rede de seguranca no banco (DEF-04).

Antes de criar o indice, a migration confere se ja existem pets com mais de um
processo ativo -- dados que o atalho manual da versao anterior permitia criar. Se
existirem, ela para com a lista, em vez de falhar com a mensagem generica do banco.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-25

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ATIVOS = "status IN ('em_analise', 'aprovado')"


def upgrade() -> None:
    duplicados = (
        op.get_bind()
        .execute(
            sa.text(
                f"SELECT pet_id FROM processos_adocao WHERE {_ATIVOS} "
                "GROUP BY pet_id HAVING count(*) > 1 ORDER BY pet_id"
            )
        )
        .scalars()
        .all()
    )
    if duplicados:
        raise RuntimeError(
            f"Pets com mais de um processo ativo: {list(duplicados)}. "
            "Cancele os processos excedentes antes de aplicar esta migration."
        )

    op.create_index(
        "uq_processo_adocao_pet_ativo",
        "processos_adocao",
        ["pet_id"],
        unique=True,
        postgresql_where=sa.text(_ATIVOS),
    )


def downgrade() -> None:
    op.drop_index("uq_processo_adocao_pet_ativo", table_name="processos_adocao")
