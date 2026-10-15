"""Schemas do apadrinhamento (fase 3, H7)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.esquemas.comuns import IdNoCorpo, ValorPositivo


class ApadrinhamentoCriar(BaseModel):
    padrinho_id: IdNoCorpo
    pet_id: IdNoCorpo
    valor_mensal: ValorPositivo
    data_inicio: date


class ApadrinhamentoEncerrar(BaseModel):
    data_fim: date


class ApadrinhamentoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    padrinho_id: int
    padrinho_nome: str
    pet_id: int
    pet_nome: str
    valor_mensal: Decimal
    data_inicio: date
    data_fim: date | None
    ativo: bool
    criado_em: datetime


class PadrinhosDoPet(BaseModel):
    """O que a ficha do pet mostra a qualquer perfil: so a contagem, sem nomes (H7.6)."""

    pet_id: int
    ativos: int
