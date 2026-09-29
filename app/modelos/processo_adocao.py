"""Processo de adocao de um pet por um adotante (RF14-18).

RN02/RF17: um pet so pode ter UM processo com status 'finalizado'. Isso e garantido
em duas camadas independentes:
  1) Aqui no banco, via indice unico parcial (so considera linhas com status='finalizado')
     -- e a rede de seguranca que sobrevive mesmo a bugs futuros na camada de servico.
  2) Na camada de servico (app/servicos/processo_adocao.py), via SELECT ... FOR UPDATE
     no pet antes de finalizar, cobrindo a corrida entre duas requisicoes concorrentes
     (RNF18): a segunda requisicao, ao tentar commitar, esbarra nesse indice e recebe
     um erro tratado como ConflitoError (409).

Um pet tambem so pode ter UM processo ativo (em analise ou aprovado) por vez: a
situacao de adocao do pet e consequencia desse processo, e dois ativos deixariam o
pet 'disponivel' ou 'adotado' conforme a ordem em que fossem encerrados (DEF-04).
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modelos.enums import StatusProcessoAdocao, coluna_enum

if TYPE_CHECKING:
    from app.modelos.adotante import Adotante
    from app.modelos.pet import Pet


class ProcessoAdocao(Base):
    __tablename__ = "processos_adocao"
    __table_args__ = (
        Index(
            "uq_processo_adocao_pet_finalizado",
            "pet_id",
            unique=True,
            postgresql_where="status = 'finalizado'",
        ),
        Index(
            "uq_processo_adocao_pet_ativo",
            "pet_id",
            unique=True,
            postgresql_where="status IN ('em_analise', 'aprovado')",
        ),
        Index("ix_processos_adocao_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="RESTRICT"), index=True)
    adotante_id: Mapped[int] = mapped_column(
        ForeignKey("adotantes.id", ondelete="RESTRICT"), index=True
    )
    responsavel_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[StatusProcessoAdocao] = mapped_column(
        coluna_enum(StatusProcessoAdocao, "status_processo_adocao"),
        nullable=False,
        default=StatusProcessoAdocao.EM_ANALISE,
    )
    # Suporta a RN01: exigido = True para finalizar um pet 'em_tratamento_medico'.
    acompanhamento_medico_em_dia: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    pet: Mapped["Pet"] = relationship(back_populates="processos_adocao")  # noqa: F821
    adotante: Mapped["Adotante"] = relationship(back_populates="processos_adocao")  # noqa: F821
