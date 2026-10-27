"""Atendimento da ficha clinica do pet (fase 2, H3).

O atendimento nao e editado nem apagado: corrige-se anulando com motivo e registrando de
novo (D8). O pet nao tem relationship para ca de proposito -- assim nenhum cascade apaga
historico clinico junto com o pet (A-09), e o banco recusa apagar um pet que tenha
atendimentos (RESTRICT).
"""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modelos.usuario import Usuario


class AtendimentoClinico(Base):
    __tablename__ = "atendimentos_clinicos"
    __table_args__ = (
        Index("ix_atendimentos_clinicos_pet_data", "pet_id", "data_atendimento"),
        # Anulacao e tudo ou nada: quando, quem e por que.
        CheckConstraint(
            "(anulado_em IS NULL AND anulado_por_id IS NULL AND motivo_anulacao IS NULL)"
            " OR (anulado_em IS NOT NULL AND anulado_por_id IS NOT NULL"
            " AND motivo_anulacao IS NOT NULL)",
            name="ck_atendimentos_clinicos_anulacao_completa",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="RESTRICT"))
    veterinario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    data_atendimento: Mapped[date] = mapped_column(Date, nullable=False)
    anamnese: Mapped[str] = mapped_column(String(5000), nullable=False)
    diagnostico: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    conduta: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    anulado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    anulado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True
    )
    motivo_anulacao: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # lazy="raise": os nomes so existem quando a consulta pede (repositorio). Esquecer de
    # carregar vira erro claro no teste, nao uma consulta escondida numa sessao async.
    veterinario: Mapped["Usuario"] = relationship(foreign_keys=[veterinario_id], lazy="raise")
    anulado_por: Mapped["Usuario | None"] = relationship(
        foreign_keys=[anulado_por_id], lazy="raise"
    )

    @property
    def veterinario_nome(self) -> str:
        return self.veterinario.nome

    @property
    def anulado_por_nome(self) -> str | None:
        return self.anulado_por.nome if self.anulado_por is not None else None
