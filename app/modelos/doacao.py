"""Doacao pontual ou recorrente (RF12, RF13). RN05: valor sempre > 0."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modelos.enums import FrequenciaContribuicao, coluna_enum

if TYPE_CHECKING:
    from app.modelos.padrinho import Padrinho


class Doacao(Base):
    __tablename__ = "doacoes"
    __table_args__ = (CheckConstraint("valor > 0", name="ck_doacao_valor_positivo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # Doacao pode vir de um padrinho cadastrado OU de um doador avulso (sem cadastro).
    padrinho_id: Mapped[int | None] = mapped_column(
        ForeignKey("padrinhos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    doador_nome: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # Destino opcional (H8): sem pet, e doacao geral da ONG. RESTRICT: apagar o pet nao
    # leva o registro financeiro (A-09).
    pet_id: Mapped[int | None] = mapped_column(
        ForeignKey("pets.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tipo: Mapped[FrequenciaContribuicao] = mapped_column(
        coluna_enum(FrequenciaContribuicao, "tipo_doacao"), nullable=False
    )

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    padrinho: Mapped["Padrinho | None"] = relationship(back_populates="doacoes")  # noqa: F821
