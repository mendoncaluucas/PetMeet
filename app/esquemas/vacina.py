"""Schemas do catalogo de vacinas e do cartao de vacinacao (fase 2, H4 e H5)."""

import enum
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.esquemas.atendimento_clinico import AtendimentoAnular
from app.esquemas.comuns import contrato_sem_nulo_em
from app.modelos.enums import EspeciePet
from app.modelos.vacina import normalizar_nome_vacina


def _aparar(valor: object) -> object:
    """Texto so com espacos conta como nao informado."""
    if isinstance(valor, str):
        return valor.strip() or None
    return valor


# ------------------------------------------------------------------ catalogo


class VacinaCriar(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    # Nulo = qualquer especie.
    especie: EspeciePet | None = None
    intervalo_reforco_dias: int | None = Field(None, ge=1, le=3650)

    @field_validator("nome", mode="before")
    @classmethod
    def aparar_nome(cls, valor: object) -> object:
        valor = _aparar(valor)
        # NFC antes do limite de tamanho: o acento separado (NFD) conta um caractere a mais.
        return normalizar_nome_vacina(valor) if isinstance(valor, str) else valor


class VacinaAtualizar(BaseModel):
    """PATCH do catalogo. A especie nao muda: as aplicacoes ja feitas dependem dela.

    nome e ativa nao aceitam null; o intervalo aceita, e null tira a sugestao de reforco.
    """

    model_config = ConfigDict(json_schema_extra=contrato_sem_nulo_em("nome", "ativa"))

    nome: str | None = Field(None, min_length=1, max_length=100)
    intervalo_reforco_dias: int | None = Field(None, ge=1, le=3650)
    ativa: bool | None = None

    @field_validator("nome", mode="before")
    @classmethod
    def aparar_nome(cls, valor: object) -> object:
        valor = _aparar(valor)
        # NFC antes do limite de tamanho: o acento separado (NFD) conta um caractere a mais.
        return normalizar_nome_vacina(valor) if isinstance(valor, str) else valor

    @model_validator(mode="after")
    def recusar_nulo(self) -> "VacinaAtualizar":
        for campo in ("nome", "ativa"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} nao aceita nulo; para nao alterar, deixe de envia-lo")
        return self


class VacinaResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    especie: EspeciePet | None
    intervalo_reforco_dias: int | None
    ativa: bool


# ------------------------------------------------------------------- cartao


class AplicacaoCriar(BaseModel):
    # O veterinario vem do login, nunca do corpo: campo extra e ignorado.
    vacina_id: int
    data_aplicacao: date
    proxima_dose: date | None = None
    lote: str | None = Field(None, max_length=50)
    observacao: str | None = Field(None, max_length=500)

    @field_validator("lote", "observacao", mode="before")
    @classmethod
    def aparar_textos(cls, valor: object) -> object:
        return _aparar(valor)

    @model_validator(mode="after")
    def proxima_dose_depois_da_aplicacao(self) -> "AplicacaoCriar":
        # Pode estar no passado: e assim que se registra um cartao antigo (H5.2).
        if self.proxima_dose is not None and self.proxima_dose <= self.data_aplicacao:
            raise ValueError("proxima_dose precisa ser depois da data_aplicacao")
        return self


class AplicacaoAnular(AtendimentoAnular):
    """Mesmo contrato da anulacao de atendimento: motivo obrigatorio (H5.6)."""


class AplicacaoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pet_id: int
    vacina_id: int
    vacina_nome: str
    data_aplicacao: date
    proxima_dose: date | None
    lote: str | None
    observacao: str | None
    veterinario_id: int
    veterinario_nome: str
    criado_em: datetime
    anulado_em: datetime | None
    anulado_por_nome: str | None
    motivo_anulacao: str | None


class StatusVacina(str, enum.Enum):
    """Calculado pela proxima dose da ultima aplicacao valida (H5.7); nao fica no banco."""

    EM_DIA = "em_dia"
    VENCENDO = "vencendo"
    VENCIDA = "vencida"
    SEM_REFORCO = "sem_reforco"


class SituacaoVacina(BaseModel):
    vacina_id: int
    vacina_nome: str
    vacina_ativa: bool
    ultima_aplicacao: date
    proxima_dose: date | None
    status: StatusVacina
    # Negativo = dias de atraso. Nulo quando nao ha reforco previsto.
    dias_para_vencer: int | None


class CartaoVacinacao(BaseModel):
    pet_id: int
    # O dia (Brasilia) usado no calculo: a tela mostra o mesmo "hoje" que a API usou.
    hoje: date
    situacao: list[SituacaoVacina]
    historico: list[AplicacaoResposta]


# ------------------------------------------------------------------ alertas


class AlertaVacina(BaseModel):
    pet_id: int
    pet_nome: str
    vacina_id: int
    vacina_nome: str
    proxima_dose: date
    # So vencida ou vencendo: em dia e sem reforco nao viram alerta (H6.2).
    status: StatusVacina
    # Negativo = dias de atraso.
    dias_para_vencer: int


class AlertasVacina(BaseModel):
    # O dia (Brasilia) usado no calculo.
    hoje: date
    total_vencidas: int
    total_vencendo: int
    # As mais atrasadas primeiro; limitada pelo parametro `limite` da rota.
    itens: list[AlertaVacina]
