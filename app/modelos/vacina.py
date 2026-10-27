"""Catalogo de vacinas e aplicacoes do cartao de vacinacao (fase 2, H4 e H5).

O catalogo existe para "V10" e "v10" nao virarem duas vacinas (A-10). Vacina nao se apaga,
so se desativa: as aplicacoes antigas continuam apontando para ela.

A aplicacao segue a regra da ficha clinica: nao se edita nem se apaga, anula-se com motivo
(D8). O pet nao tem relationship para ca, entao nenhum cascade leva o cartao junto (A-09).
"""

import unicodedata
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base
from app.modelos.enums import EspeciePet, coluna_enum

if TYPE_CHECKING:
    from app.modelos.usuario import Usuario


def normalizar_nome_vacina(nome: str) -> str:
    """Forma gravada do nome: sem espacos nas pontas e em NFC. O mesmo "Antirrábica" pode
    chegar com o acento composto (NFC) ou separado da letra (NFD), e eram dois nomes."""
    return unicodedata.normalize("NFC", nome.strip())


def chave_do_nome_vacina(nome: str) -> str:
    """Chave da unicidade (H4.2): sem maiusculas, sem espacos nas pontas, em NFC.

    Calculada aqui e nao com lower() no banco: o lower() do Postgres so trata acentos
    quando o banco tem collation como en_US.utf8. Com collation C, comum em banco
    gerenciado, "ANTIRRÁBICA" e "Antirrábica" passariam como duas vacinas.
    """
    return normalizar_nome_vacina(nome).casefold()


class Vacina(Base):
    __tablename__ = "vacinas"
    __table_args__ = (
        UniqueConstraint("nome_chave", name="uq_vacinas_nome_chave"),
        CheckConstraint(
            "intervalo_reforco_dias IS NULL OR intervalo_reforco_dias > 0",
            name="ck_vacinas_intervalo_positivo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    # Preenchida sozinha a cada mudanca de nome (validates abaixo). Unica no banco: e ela
    # que garante "V10" == " v10 " (H4.2), qualquer que seja o caminho da gravacao.
    # 200: o casefold pode alongar o texto ("ß" vira "ss").
    nome_chave: Mapped[str] = mapped_column(String(200), nullable=False)
    # Nulo = serve para qualquer especie (antirrabica, por exemplo).
    especie: Mapped[EspeciePet | None] = mapped_column(
        coluna_enum(EspeciePet, "especie_pet"), nullable=True
    )
    intervalo_reforco_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ativa: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @validates("nome")
    def _manter_chave(self, _campo: str, nome: str) -> str:
        nome = normalizar_nome_vacina(nome)
        self.nome_chave = chave_do_nome_vacina(nome)
        return nome


class AplicacaoVacina(Base):
    __tablename__ = "aplicacoes_vacina"
    __table_args__ = (
        # A mesma vacina, no mesmo pet e no mesmo dia, uma aplicacao valida so (H5.4). As
        # anuladas ficam de fora: anular e registrar de novo tem de funcionar.
        Index(
            "uq_aplicacoes_vacina_valida_por_dia",
            "pet_id",
            "vacina_id",
            "data_aplicacao",
            unique=True,
            postgresql_where=text("anulado_em IS NULL"),
        ),
        CheckConstraint(
            "proxima_dose IS NULL OR proxima_dose > data_aplicacao",
            name="ck_aplicacoes_vacina_proxima_dose_depois",
        ),
        CheckConstraint(
            "(anulado_em IS NULL AND anulado_por_id IS NULL AND motivo_anulacao IS NULL)"
            " OR (anulado_em IS NOT NULL AND anulado_por_id IS NOT NULL"
            " AND motivo_anulacao IS NOT NULL)",
            name="ck_aplicacoes_vacina_anulacao_completa",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="RESTRICT"))
    vacina_id: Mapped[int] = mapped_column(ForeignKey("vacinas.id", ondelete="RESTRICT"))
    veterinario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    data_aplicacao: Mapped[date] = mapped_column(Date, nullable=False)
    proxima_dose: Mapped[date | None] = mapped_column(Date, nullable=True)
    lote: Mapped[str | None] = mapped_column(String(50), nullable=True)
    observacao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    anulado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    anulado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=True
    )
    motivo_anulacao: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # lazy="raise", como na ficha clinica: os nomes so existem quando a consulta pede.
    vacina: Mapped[Vacina] = relationship(lazy="raise")
    veterinario: Mapped["Usuario"] = relationship(foreign_keys=[veterinario_id], lazy="raise")
    anulado_por: Mapped["Usuario | None"] = relationship(
        foreign_keys=[anulado_por_id], lazy="raise"
    )

    @property
    def vacina_nome(self) -> str:
        return self.vacina.nome

    @property
    def veterinario_nome(self) -> str:
        return self.veterinario.nome

    @property
    def anulado_por_nome(self) -> str | None:
        return self.anulado_por.nome if self.anulado_por is not None else None
