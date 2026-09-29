"""Pessoa interessada em adotar (RF06, RF07). Dado pessoal sensivel: LGPD (RN07)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modelos.processo_adocao import ProcessoAdocao


class Adotante(Base):
    __tablename__ = "adotantes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    cpf: Mapped[str] = mapped_column(String(11), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    telefone: Mapped[str] = mapped_column(String(20), nullable=False)
    endereco: Mapped[str] = mapped_column(String(255), nullable=False)
    # Inativo: fora das listagens e sem processo novo. Quem tem processo no historico
    # nao pode ser excluido -- so inativado (DEF-13).
    ativo: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    processos_adocao: Mapped[list["ProcessoAdocao"]] = relationship(  # noqa: F821
        back_populates="adotante"
    )
