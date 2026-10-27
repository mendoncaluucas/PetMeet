"""Gasto da ONG (fase 3, H9).

Gasto nao se edita nem se apaga: corrige-se por estorno (D13). O estorno e outro gasto, com
valor negativo, a data do dia da correcao, a mesma categoria e o mesmo pet, ligado ao original
por estorno_de_id. Assim o total de um mes ja publicado nao muda depois -- o estorno aparece
no mes em que foi feito. Totais e portal somam todos os lancamentos, sem filtro especial.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modelos.enums import CategoriaGasto, coluna_enum

if TYPE_CHECKING:
    from app.modelos.pet import Pet
    from app.modelos.usuario import Usuario

# Lancamento comum e positivo e sem motivo; estorno e negativo, aponta o original e tem motivo.
SINAL_DO_LANCAMENTO = (
    "(estorno_de_id IS NULL AND valor > 0 AND motivo_estorno IS NULL)"
    " OR (estorno_de_id IS NOT NULL AND valor < 0 AND motivo_estorno IS NOT NULL)"
)


class Gasto(Base):
    __tablename__ = "gastos"
    __table_args__ = (CheckConstraint(SINAL_DO_LANCAMENTO, name="ck_gastos_sinal_do_lancamento"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    categoria: Mapped[CategoriaGasto] = mapped_column(
        coluna_enum(CategoriaGasto, "categoria_gasto"), nullable=False
    )
    descricao: Mapped[str] = mapped_column(String(500), nullable=False)
    pet_id: Mapped[int | None] = mapped_column(
        ForeignKey("pets.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    registrado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    # UNIQUE: cada gasto e estornado uma vez so, tambem com dois pedidos ao mesmo tempo.
    estorno_de_id: Mapped[int | None] = mapped_column(
        ForeignKey("gastos.id", ondelete="RESTRICT"), nullable=True, unique=True
    )
    motivo_estorno: Mapped[str | None] = mapped_column(String(500), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pet: Mapped["Pet | None"] = relationship(lazy="raise")
    # O estorno deste lancamento, se houver (so leitura): a listagem mostra o original como
    # estornado e o estorno logo abaixo, numa consulta so.
    estorno: Mapped["Gasto | None"] = relationship(
        "Gasto",
        primaryjoin="Gasto.id == remote(foreign(Gasto.estorno_de_id))",
        uselist=False,
        viewonly=True,
        lazy="raise",
    )
    registrado_por: Mapped["Usuario"] = relationship(lazy="raise")

    @property
    def pet_nome(self) -> str | None:
        return self.pet.nome if self.pet is not None else None

    @property
    def registrado_por_nome(self) -> str:
        return self.registrado_por.nome

    @property
    def estornado_em(self) -> date | None:
        """Data do estorno deste lancamento (o mes em que ele saiu dos totais)."""
        return self.estorno.data if self.estorno is not None else None
