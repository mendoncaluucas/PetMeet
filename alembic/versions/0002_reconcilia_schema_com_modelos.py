"""reconcilia o schema do banco com os modelos

A migration 0001 foi escrita a mao e divergia dos modelos em 19 pontos -- o
`alembic check` falhava, e qualquer `revision --autogenerate` arrastaria essas
diferencas junto com a mudanca pretendida. Esta migration faz o banco seguir o
que os modelos declaram:

- colunas criado_em/atualizado_em passam a NOT NULL (todas tem server_default now());
- CPF de adotantes/padrinhos e email de usuarios tinham uma UNIQUE CONSTRAINT e,
  alem dela, um indice comum redundante. Ficam com um unico indice UNIQUE.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-25

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUNAS_DE_TEMPO = (
    ("adotantes", "criado_em"),
    ("apadrinhamentos", "criado_em"),
    ("doacoes", "criado_em"),
    ("logs_auditoria", "criado_em"),
    ("padrinhos", "criado_em"),
    ("pets", "criado_em"),
    ("pets", "atualizado_em"),
    ("processos_adocao", "criado_em"),
    ("processos_adocao", "atualizado_em"),
    ("usuarios", "criado_em"),
)

# (tabela, coluna, constraint unica da 0001, indice)
_UNICOS = (
    ("adotantes", "cpf", "uq_adotantes_cpf", "ix_adotantes_cpf"),
    ("padrinhos", "cpf", "uq_padrinhos_cpf", "ix_padrinhos_cpf"),
    ("usuarios", "email", "uq_usuarios_email", "ix_usuarios_email"),
)


def upgrade() -> None:
    for tabela, coluna in _COLUNAS_DE_TEMPO:
        op.alter_column(tabela, coluna, existing_type=sa.DateTime(timezone=True), nullable=False)

    for tabela, coluna, constraint, indice in _UNICOS:
        op.drop_index(indice, table_name=tabela)
        op.drop_constraint(constraint, tabela, type_="unique")
        op.create_index(indice, tabela, [coluna], unique=True)


def downgrade() -> None:
    for tabela, coluna, constraint, indice in _UNICOS:
        op.drop_index(indice, table_name=tabela)
        op.create_unique_constraint(constraint, tabela, [coluna])
        op.create_index(indice, tabela, [coluna])

    for tabela, coluna in _COLUNAS_DE_TEMPO:
        op.alter_column(tabela, coluna, existing_type=sa.DateTime(timezone=True), nullable=True)
