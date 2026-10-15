"""Ficha do pet: dados cadastrais, status de saude e situacao de adocao (RF01-05)."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modelos.enums import EspeciePet, SituacaoAdocaoPet, StatusSaudePet, coluna_enum

if TYPE_CHECKING:
    from app.modelos.processo_adocao import ProcessoAdocao


class Pet(Base):
    __tablename__ = "pets"
    __table_args__ = (
        Index("ix_pets_situacao_adocao", "situacao_adocao"),
        Index("ix_pets_status_saude", "status_saude"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    especie: Mapped[EspeciePet] = mapped_column(
        coluna_enum(EspeciePet, "especie_pet"), nullable=False
    )
    idade: Mapped[int] = mapped_column(Integer, nullable=False)
    data_resgate: Mapped[date] = mapped_column(Date, nullable=False)

    status_saude: Mapped[StatusSaudePet] = mapped_column(
        coluna_enum(StatusSaudePet, "status_saude_pet"),
        nullable=False,
        default=StatusSaudePet.SAUDAVEL,
    )
    # Obrigatorio quando status_saude == EM_TRATAMENTO_MEDICO (RF16). Validado na camada de servico.
    doenca_atual: Mapped[str | None] = mapped_column(String(255), nullable=True)

    situacao_adocao: Mapped[SituacaoAdocaoPet] = mapped_column(
        coluna_enum(SituacaoAdocaoPet, "situacao_adocao_pet"),
        nullable=False,
        default=SituacaoAdocaoPet.DISPONIVEL,
    )

    foto_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    processos_adocao: Mapped[list["ProcessoAdocao"]] = relationship(  # noqa: F821
        back_populates="pet", cascade="all, delete-orphan"
    )
