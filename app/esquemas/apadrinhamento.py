"""Schemas do apadrinhamento (fase 3, H7) e do esperado x recebido (H10)."""

import enum
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


class SituacaoDoMes(str, enum.Enum):
    """Situacao de um padrinho num mes (H10.3). Nao e coluna: sai do calculo."""

    EM_DIA = "em_dia"
    PARCIAL = "parcial"
    SEM_DOACAO = "sem_doacao"
    # Mes corrente ainda nao pago: nao e atraso enquanto o mes nao acaba.
    EM_ANDAMENTO = "em_andamento"
    # Nenhum apadrinhamento ativo no mes: nao havia o que cobrar.
    SEM_COMPROMISSO = "sem_compromisso"


class MesDoPadrinho(BaseModel):
    mes: str
    esperado: Decimal
    recebido: Decimal
    # recebido - esperado: negativo e o que falta.
    diferenca: Decimal
    situacao: SituacaoDoMes


class EsperadoRecebido(BaseModel):
    """Um padrinho nos ultimos 12 meses, do mais recente para o mais antigo."""

    padrinho_id: int
    padrinho_nome: str
    # Meses fechados parciais ou sem doacao: o que a equipe precisa cobrar.
    meses_pendentes: int
    meses: list[MesDoPadrinho]


class PadrinhosDoPet(BaseModel):
    """O que a ficha do pet mostra a qualquer perfil: so a contagem, sem nomes (H7.6)."""

    pet_id: int
    ativos: int
