"""cartao de vacinacao

Catalogo de vacinas e aplicacoes do cartao de vacinacao (fase 2, H4 e H5).

- O nome da vacina e unico sem diferenciar maiusculas nem espacos nas pontas: "V10" e
  " v10 " sao a mesma vacina (A-10). A unicidade fica em nome_chave, calculada no Python
  (NFC + casefold), e nao num lower() do banco, que depende da collation. O catalogo
  inicial entra aqui, para existir em qualquer ambiente, nao so onde o seed rodou.
- A especie reaproveita o tipo especie_pet que ja existe (create_type=False); nula quer
  dizer "qualquer especie".
- Aplicacao segue a ficha clinica: sem edicao nem exclusao, anulacao completa (D8),
  chaves RESTRICT (A-09). Uma aplicacao valida por vacina, pet e dia (indice parcial que
  ignora as anuladas).

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-14

"""

import unicodedata
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Reforco anual: o intervalo e so a sugestao da proxima dose, a tela deixa mudar.
_CATALOGO_INICIAL = [
    ("V8", "cachorro"),
    ("V10", "cachorro"),
    ("Gripe canina", "cachorro"),
    ("Giárdia", "cachorro"),
    ("Leishmaniose", "cachorro"),
    ("Tríplice felina (V3)", "gato"),
    ("Quádrupla felina (V4)", "gato"),
    ("FeLV", "gato"),
    ("Antirrábica", None),
]


def _chave(nome: str) -> str:
    # Copia da regra de app/modelos/vacina.py (chave_do_nome_vacina), de proposito: a
    # migration nao importa o app, para nao mudar de comportamento se o app mudar.
    return unicodedata.normalize("NFC", nome.strip()).casefold()


def upgrade() -> None:
    especie_pet = postgresql.ENUM(
        "cachorro", "gato", "outro", name="especie_pet", create_type=False
    )

    vacinas = op.create_table(
        "vacinas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("nome_chave", sa.String(length=200), nullable=False),
        sa.Column("especie", especie_pet, nullable=True),
        sa.Column("intervalo_reforco_dias", sa.Integer(), nullable=True),
        sa.Column("ativa", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "intervalo_reforco_dias IS NULL OR intervalo_reforco_dias > 0",
            name="ck_vacinas_intervalo_positivo",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nome_chave", name="uq_vacinas_nome_chave"),
    )

    op.create_table(
        "aplicacoes_vacina",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pet_id", sa.Integer(), nullable=False),
        sa.Column("vacina_id", sa.Integer(), nullable=False),
        sa.Column("veterinario_id", sa.Integer(), nullable=False),
        sa.Column("data_aplicacao", sa.Date(), nullable=False),
        sa.Column("proxima_dose", sa.Date(), nullable=True),
        sa.Column("lote", sa.String(length=50), nullable=True),
        sa.Column("observacao", sa.String(length=500), nullable=True),
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
            name="ck_aplicacoes_vacina_anulacao_completa",
        ),
        sa.CheckConstraint(
            "proxima_dose IS NULL OR proxima_dose > data_aplicacao",
            name="ck_aplicacoes_vacina_proxima_dose_depois",
        ),
        sa.ForeignKeyConstraint(["anulado_por_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vacina_id"], ["vacinas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["veterinario_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_aplicacoes_vacina_valida_por_dia",
        "aplicacoes_vacina",
        ["pet_id", "vacina_id", "data_aplicacao"],
        unique=True,
        postgresql_where=sa.text("anulado_em IS NULL"),
    )

    op.bulk_insert(
        vacinas,
        [
            {
                "nome": nome,
                "nome_chave": _chave(nome),
                "especie": especie,
                "intervalo_reforco_dias": 365,
            }
            for nome, especie in _CATALOGO_INICIAL
        ],
    )


def downgrade() -> None:
    # Com aplicacoes gravadas, desfazer apagaria cartoes de vacinacao: historico clinico,
    # que o N2 nao apaga nunca. So desce com a tabela vazia (o catalogo pode ir junto).
    aplicacoes = op.get_bind().scalar(sa.text("SELECT count(*) FROM aplicacoes_vacina"))
    if aplicacoes:
        raise RuntimeError(
            f"Ha {aplicacoes} aplicacao(oes) de vacina gravada(s). Desfazer esta migration "
            "apagaria esses cartoes; exporte e remova os dados antes, se for mesmo o caso."
        )
    op.drop_index(
        "uq_aplicacoes_vacina_valida_por_dia",
        table_name="aplicacoes_vacina",
        postgresql_where=sa.text("anulado_em IS NULL"),
    )
    op.drop_table("aplicacoes_vacina")
    op.drop_table("vacinas")
