"""Schemas de gastos e estornos (fase 3, H9)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.esquemas.comuns import IdNoCorpo, ValorPositivo
from app.modelos.enums import CategoriaGasto


def _aparar(valor: object) -> object:
    """Texto so com espacos conta como vazio."""
    if isinstance(valor, str):
        return valor.strip() or None
    return valor


class GastoCriar(BaseModel):
    valor: ValorPositivo
    data: date
    categoria: CategoriaGasto
    descricao: str = Field(..., min_length=1, max_length=500)
    pet_id: IdNoCorpo | None = None

    @field_validator("descricao", mode="before")
    @classmethod
    def aparar_descricao(cls, valor: object) -> object:
        return _aparar(valor)


class EstornoCriar(BaseModel):
    """Estorno de gasto ou de doacao: o motivo e obrigatorio (H9.3)."""

    motivo: str = Field(..., min_length=1, max_length=500)

    @field_validator("motivo", mode="before")
    @classmethod
    def aparar_motivo(cls, valor: object) -> object:
        return _aparar(valor)


class GastoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # Negativo quando e um estorno.
    valor: Decimal
    data: date
    categoria: CategoriaGasto
    descricao: str
    pet_id: int | None
    pet_nome: str | None
    registrado_por_nome: str
    estorno_de_id: int | None
    motivo_estorno: str | None
    # Preenchido no original que ja foi estornado: a data do estorno.
    estornado_em: date | None
    criado_em: datetime


class LancamentoAuditado(BaseModel):
    """O que vai para a auditoria a cada gasto, doacao ou estorno (H9.7)."""

    id: int
    valor: Decimal
    data: date
    estorno_de_id: int | None
    motivo_estorno: str | None
