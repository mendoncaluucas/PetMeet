"""um processo de adocao ativo por pet

Indice unico parcial: um pet so pode ter um processo em analise ou aprovado por vez.
A situacao de adocao do pet deixa de ser editavel a mao e passa a ser so efeito do
processo; este indice e a rede de seguranca no banco (DEF-04).

Antes de criar o indice, a migration confere se ja existem pets com mais de um
processo ativo -- dados que o atalho manual da versao anterior permitia criar. Se
existirem, ela para com a lista, em vez de falhar com a mensagem generica do banco.

Ela tambem alinha a situacao dos pets que o atalho deixou incoerente com os
processos. Sem a rota manual, um pet 'em processo' sem processo ativo ficaria preso:
nao abriria processo novo e nao haveria como corrigi-lo. O alinhamento nao e desfeito
no downgrade.

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
_TEM_PROCESSO = "SELECT 1 FROM processos_adocao p WHERE p.pet_id = pets.id AND p.{condicao}"


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

    _alinhar_situacao_dos_pets()

    op.create_index(
        "uq_processo_adocao_pet_ativo",
        "processos_adocao",
        ["pet_id"],
        unique=True,
        postgresql_where=sa.text(_ATIVOS),
    )


def _alinhar_situacao_dos_pets() -> None:
    """'em processo' sem processo ativo volta a 'disponivel'; 'disponivel' com processo
    ativo passa a 'em processo'. Pet 'adotado' nao e tocado (RN04) -- so listado."""
    conexao = op.get_bind()
    ativo = _TEM_PROCESSO.format(condicao=_ATIVOS)
    for de, para, condicao in (
        ("em_processo_adocao", "disponivel", f"NOT EXISTS ({ativo})"),
        ("disponivel", "em_processo_adocao", f"EXISTS ({ativo})"),
    ):
        alterados = conexao.execute(
            sa.text(
                f"UPDATE pets SET situacao_adocao = '{para}', atualizado_em = now() "
                f"WHERE situacao_adocao = '{de}' AND {condicao} RETURNING id"
            )
        ).scalars()
        if ids := sorted(alterados):
            print(f"0003: pets {ids} passaram de '{de}' para '{para}'.")

    finalizado = _TEM_PROCESSO.format(condicao="status = 'finalizado'")
    suspeitos = conexao.execute(
        sa.text(
            "SELECT id FROM pets WHERE situacao_adocao = 'adotado' "
            f"AND NOT EXISTS ({finalizado}) ORDER BY id"
        )
    ).scalars()
    if ids := list(suspeitos):
        print(f"0003: pets {ids} estao 'adotado' sem processo finalizado -- conferir a mao.")


def downgrade() -> None:
    op.drop_index("uq_processo_adocao_pet_ativo", table_name="processos_adocao")
