"""gastos e estornos

Fase 3, H9 (D13): gasto e doacao nao se editam nem se apagam -- corrigem-se por estorno.

- Tabela gastos: valor, data, categoria, descricao, pet opcional e quem registrou.
- O estorno e um lancamento negativo, com a data da correcao, ligado ao original por
  estorno_de_id (UNIQUE: um estorno por lancamento). Vale para gasto e para doacao.
- Doacoes: o CHECK valor > 0 (RN05) vira "positivo, ou negativo quando e estorno", com
  motivo obrigatorio no estorno. Ganham quem registrou (nulo nas anteriores, que nao
  guardavam isso).

O autogenerate nao compara CHECK: a troca do CHECK das doacoes so existe aqui.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Copia da regra de app/modelos/gasto.py, de proposito: a migration nao importa o app.
_SINAL_DO_LANCAMENTO = (
    "(estorno_de_id IS NULL AND valor > 0 AND motivo_estorno IS NULL)"
    " OR (estorno_de_id IS NOT NULL AND valor < 0 AND motivo_estorno IS NOT NULL)"
)
_CATEGORIAS = (
    "alimentacao",
    "veterinario_medicamentos",
    "vacinas",
    "higiene_limpeza",
    "estrutura_manutencao",
    "transporte",
    "outros",
)


def upgrade() -> None:
    categoria = postgresql.ENUM(*_CATEGORIAS, name="categoria_gasto")
    categoria.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "gastos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("valor", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column(
            "categoria",
            postgresql.ENUM(*_CATEGORIAS, name="categoria_gasto", create_type=False),
            nullable=False,
        ),
        sa.Column("descricao", sa.String(length=500), nullable=False),
        sa.Column("pet_id", sa.Integer(), nullable=True),
        sa.Column("registrado_por_id", sa.Integer(), nullable=False),
        sa.Column("estorno_de_id", sa.Integer(), nullable=True),
        sa.Column("motivo_estorno", sa.String(length=500), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(_SINAL_DO_LANCAMENTO, name="ck_gastos_sinal_do_lancamento"),
        sa.ForeignKeyConstraint(["estorno_de_id"], ["gastos.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["registrado_por_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("estorno_de_id", name="gastos_estorno_de_id_key"),
    )
    op.create_index("ix_gastos_data", "gastos", ["data"], unique=False)
    op.create_index("ix_gastos_pet_id", "gastos", ["pet_id"], unique=False)

    op.add_column("doacoes", sa.Column("registrado_por_id", sa.Integer(), nullable=True))
    op.add_column("doacoes", sa.Column("estorno_de_id", sa.Integer(), nullable=True))
    op.add_column("doacoes", sa.Column("motivo_estorno", sa.String(length=500), nullable=True))
    op.create_unique_constraint("doacoes_estorno_de_id_key", "doacoes", ["estorno_de_id"])
    op.create_foreign_key(
        "doacoes_registrado_por_id_fkey",
        "doacoes",
        "usuarios",
        ["registrado_por_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "doacoes_estorno_de_id_fkey",
        "doacoes",
        "doacoes",
        ["estorno_de_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("ck_doacao_valor_positivo", "doacoes", type_="check")
    op.create_check_constraint("ck_doacao_sinal_do_lancamento", "doacoes", _SINAL_DO_LANCAMENTO)


def downgrade() -> None:
    # Voltar apagaria gastos e estornos: registro financeiro, que o N2 nao apaga nunca.
    conexao = op.get_bind()
    gastos = conexao.scalar(sa.text("SELECT count(*) FROM gastos"))
    estornos = conexao.scalar(
        sa.text("SELECT count(*) FROM doacoes WHERE estorno_de_id IS NOT NULL")
    )
    if gastos or estornos:
        raise RuntimeError(
            f"Ha {gastos} gasto(s) e {estornos} estorno(s) de doacao gravados. Desfazer esta "
            "migration apagaria esse registro financeiro; exporte e remova antes, se for o caso."
        )

    op.drop_constraint("ck_doacao_sinal_do_lancamento", "doacoes", type_="check")
    op.create_check_constraint("ck_doacao_valor_positivo", "doacoes", "valor > 0")
    op.drop_constraint("doacoes_estorno_de_id_fkey", "doacoes", type_="foreignkey")
    op.drop_constraint("doacoes_registrado_por_id_fkey", "doacoes", type_="foreignkey")
    op.drop_constraint("doacoes_estorno_de_id_key", "doacoes", type_="unique")
    op.drop_column("doacoes", "motivo_estorno")
    op.drop_column("doacoes", "estorno_de_id")
    op.drop_column("doacoes", "registrado_por_id")

    op.drop_index("ix_gastos_pet_id", table_name="gastos")
    op.drop_index("ix_gastos_data", table_name="gastos")
    op.drop_table("gastos")
    postgresql.ENUM(name="categoria_gasto").drop(op.get_bind(), checkfirst=True)
