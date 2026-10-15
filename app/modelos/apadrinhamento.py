"""Apadrinhamento: compromisso mensal de um padrinho com um pet (fase 3, H7).

D11: e sempre mensal -- o padrinho combina um valor por mes. Doacao pontual nao precisa de
apadrinhamento. Ativo enquanto data_fim e nula; encerrado, o mesmo padrinho pode apadrinhar
o mesmo pet de novo (A-08: a unicidade vale so entre os ativos).

Nao ha relationship do pet nem do padrinho para ca, e as chaves sao RESTRICT: apagar um pet
ou um padrinho nao leva o historico do que foi combinado (A-09). A versao recebida usava
cascade e ON DELETE CASCADE.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modelos.padrinho import Padrinho
    from app.modelos.pet import Pet


class Apadrinhamento(Base):
    __tablename__ = "apadrinhamentos"
    __table_args__ = (
        Index(
            "uq_apadrinhamento_ativo",
            "padrinho_id",
            "pet_id",
            unique=True,
            postgresql_where=text("data_fim IS NULL"),
        ),
        CheckConstraint("valor_mensal > 0", name="ck_apadrinhamento_valor_positivo"),
        CheckConstraint(
            "data_fim IS NULL OR data_fim >= data_inicio", name="ck_apadrinhamento_fim_depois"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    padrinho_id: Mapped[int] = mapped_column(
        ForeignKey("padrinhos.id", ondelete="RESTRICT"), index=True
    )
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="RESTRICT"), index=True)
    valor_mensal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # lazy="raise": os nomes so existem quando a consulta pede (repositorio).
    padrinho: Mapped["Padrinho"] = relationship(lazy="raise")
    pet: Mapped["Pet"] = relationship(lazy="raise")

    @property
    def ativo(self) -> bool:
        return self.data_fim is None

    @property
    def padrinho_nome(self) -> str:
        return self.padrinho.nome

    @property
    def pet_nome(self) -> str:
        return self.pet.nome
