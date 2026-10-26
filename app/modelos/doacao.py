"""Doacao pontual ou recorrente (RF12, RF13).

RN05: doacao e sempre positiva. A unica linha negativa e o estorno (fase 3, H9, D13): outro
lancamento, com a data do dia da correcao, ligado ao original por estorno_de_id. O total de
um mes ja publicado nao muda depois.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modelos.enums import FrequenciaContribuicao, coluna_enum
from app.modelos.gasto import SINAL_DO_LANCAMENTO

if TYPE_CHECKING:
    from app.modelos.padrinho import Padrinho
    from app.modelos.usuario import Usuario


class Doacao(Base):
    __tablename__ = "doacoes"
    __table_args__ = (CheckConstraint(SINAL_DO_LANCAMENTO, name="ck_doacao_sinal_do_lancamento"),)

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

    # Quem registrou. Nulo nas doacoes anteriores a fase 3, que nao guardavam isso.
    registrado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True
    )
    # UNIQUE: cada doacao e estornada uma vez so, tambem com dois pedidos ao mesmo tempo.
    estorno_de_id: Mapped[int | None] = mapped_column(
        ForeignKey("doacoes.id", ondelete="RESTRICT"), nullable=True, unique=True
    )
    motivo_estorno: Mapped[str | None] = mapped_column(String(500), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    padrinho: Mapped["Padrinho | None"] = relationship(back_populates="doacoes")  # noqa: F821
    registrado_por: Mapped["Usuario | None"] = relationship(lazy="raise")
    # O estorno deste lancamento, se houver (so leitura): a listagem mostra o original como
    # estornado e o estorno logo abaixo, numa consulta so.
    estorno: Mapped["Doacao | None"] = relationship(
        "Doacao",
        primaryjoin="Doacao.id == remote(foreign(Doacao.estorno_de_id))",
        uselist=False,
        viewonly=True,
        lazy="raise",
    )

    @property
    def registrado_por_nome(self) -> str | None:
        return self.registrado_por.nome if self.registrado_por is not None else None

    @property
    def estornado_em(self) -> date | None:
        """Data do estorno deste lancamento (o mes em que ele saiu dos totais)."""
        return self.estorno.data if self.estorno is not None else None
