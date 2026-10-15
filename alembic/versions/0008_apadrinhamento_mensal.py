"""apadrinhamento mensal e doacao com destino

Fase 3, H7 e H8.

- Apadrinhamento vira compromisso mensal (D11): ganha valor_mensal e data_fim (ativo
  enquanto nula) e perde ativo e frequencia, herdadas e sem uso. O tipo
  frequencia_contribuicao so servia a essa coluna e sai junto.
- A unicidade passa a valer so entre os ativos: encerrado, o mesmo padrinho pode
  apadrinhar o mesmo pet de novo (A-08).
- As chaves de apadrinhamento eram ON DELETE CASCADE: apagar um pet ou um padrinho
  levaria o historico do que foi combinado. Passam a RESTRICT (A-09).
- Doacao ganha um pet de destino opcional; as doacoes ja gravadas ficam sem destino.

A tabela apadrinhamentos nunca teve rota e esta vazia em todos os ambientes. A migration
confere: com linhas, nao ha como inventar o valor mensal delas, e ela recusa.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _recusar_se_houver_apadrinhamentos(acao: str) -> None:
    linhas = op.get_bind().scalar(sa.text("SELECT count(*) FROM apadrinhamentos"))
    if linhas:
        raise RuntimeError(
            f"Ha {linhas} apadrinhamento(s) gravado(s). {acao} exigiria inventar dados "
            "(valor mensal ou frequencia) para eles; trate esses registros antes."
        )


def upgrade() -> None:
    _recusar_se_houver_apadrinhamentos("Converter para o apadrinhamento mensal")

    op.drop_constraint("uq_apadrinhamento_padrinho_pet", "apadrinhamentos", type_="unique")
    op.drop_column("apadrinhamentos", "ativo")
    op.drop_column("apadrinhamentos", "frequencia")
    postgresql.ENUM(name="frequencia_contribuicao").drop(op.get_bind(), checkfirst=True)

    op.add_column(
        "apadrinhamentos",
        sa.Column("valor_mensal", sa.Numeric(precision=10, scale=2), nullable=False),
    )
    op.add_column("apadrinhamentos", sa.Column("data_fim", sa.Date(), nullable=True))
    op.create_check_constraint(
        "ck_apadrinhamento_valor_positivo", "apadrinhamentos", "valor_mensal > 0"
    )
    op.create_check_constraint(
        "ck_apadrinhamento_fim_depois",
        "apadrinhamentos",
        "data_fim IS NULL OR data_fim >= data_inicio",
    )
    op.create_index(
        "uq_apadrinhamento_ativo",
        "apadrinhamentos",
        ["padrinho_id", "pet_id"],
        unique=True,
        postgresql_where=sa.text("data_fim IS NULL"),
    )

    for coluna, tabela in (("pet_id", "pets"), ("padrinho_id", "padrinhos")):
        nome = f"apadrinhamentos_{coluna}_fkey"
        op.drop_constraint(nome, "apadrinhamentos", type_="foreignkey")
        op.create_foreign_key(
            nome, "apadrinhamentos", tabela, [coluna], ["id"], ondelete="RESTRICT"
        )

    op.add_column("doacoes", sa.Column("pet_id", sa.Integer(), nullable=True))
    op.create_index("ix_doacoes_pet_id", "doacoes", ["pet_id"], unique=False)
    op.create_foreign_key(
        "doacoes_pet_id_fkey", "doacoes", "pets", ["pet_id"], ["id"], ondelete="RESTRICT"
    )


def downgrade() -> None:
    # Voltar apagaria o valor combinado e o destino das doacoes: so com as duas coisas vazias.
    _recusar_se_houver_apadrinhamentos("Voltar ao modelo anterior")
    com_destino = op.get_bind().scalar(
        sa.text("SELECT count(*) FROM doacoes WHERE pet_id IS NOT NULL")
    )
    if com_destino:
        raise RuntimeError(
            f"Ha {com_destino} doacao(oes) com pet de destino. Voltar apagaria esse destino."
        )

    op.drop_constraint("doacoes_pet_id_fkey", "doacoes", type_="foreignkey")
    op.drop_index("ix_doacoes_pet_id", table_name="doacoes")
    op.drop_column("doacoes", "pet_id")

    for coluna, tabela in (("pet_id", "pets"), ("padrinho_id", "padrinhos")):
        nome = f"apadrinhamentos_{coluna}_fkey"
        op.drop_constraint(nome, "apadrinhamentos", type_="foreignkey")
        op.create_foreign_key(nome, "apadrinhamentos", tabela, [coluna], ["id"], ondelete="CASCADE")

    op.drop_index(
        "uq_apadrinhamento_ativo",
        table_name="apadrinhamentos",
        postgresql_where=sa.text("data_fim IS NULL"),
    )
    op.drop_constraint("ck_apadrinhamento_fim_depois", "apadrinhamentos", type_="check")
    op.drop_constraint("ck_apadrinhamento_valor_positivo", "apadrinhamentos", type_="check")
    op.drop_column("apadrinhamentos", "data_fim")
    op.drop_column("apadrinhamentos", "valor_mensal")

    frequencia = postgresql.ENUM("pontual", "recorrente", name="frequencia_contribuicao")
    frequencia.create(op.get_bind(), checkfirst=True)
    op.add_column("apadrinhamentos", sa.Column("frequencia", frequencia, nullable=False))
    op.add_column(
        "apadrinhamentos",
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_unique_constraint(
        "uq_apadrinhamento_padrinho_pet", "apadrinhamentos", ["padrinho_id", "pet_id"]
    )
