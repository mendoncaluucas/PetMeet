"""Schemas de Pet (RF01-05, RF16, RF18)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.esquemas.comuns import AtualizacaoParcialSemNulo
from app.modelos.enums import EspeciePet, SituacaoAdocaoPet, StatusSaudePet


def _sem_espacos_nas_pontas(valor: object) -> object:
    """Doenca so com espacos conta como nao informada: "   " passava como diagnostico, e a
    equipe, que pode corrigir a doenca de um pet em tratamento, apagaria o texto assim."""
    if isinstance(valor, str):
        return valor.strip() or None
    return valor


class PetCriar(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    especie: EspeciePet
    idade: int = Field(..., ge=0, le=40)
    data_resgate: date
    status_saude: StatusSaudePet = StatusSaudePet.SAUDAVEL
    doenca_atual: str | None = Field(None, max_length=255)

    @field_validator("doenca_atual", mode="before")
    @classmethod
    def limpar_doenca_atual(cls, valor: object) -> object:
        return _sem_espacos_nas_pontas(valor)

    @model_validator(mode="after")
    def validar_doenca_atual(self) -> "PetCriar":
        # RF16: se esta em tratamento medico, a doenca sendo tratada deve ser identificada.
        if self.status_saude == StatusSaudePet.EM_TRATAMENTO_MEDICO and not self.doenca_atual:
            raise ValueError(
                "doenca_atual e obrigatoria quando status_saude e 'em_tratamento_medico'"
            )
        return self


class PetAtualizar(AtualizacaoParcialSemNulo):
    nome: str | None = Field(None, min_length=1, max_length=100)
    especie: EspeciePet | None = None
    idade: int | None = Field(None, ge=0, le=40)
    data_resgate: date | None = None


class PetAtualizarStatusSaude(BaseModel):
    status_saude: StatusSaudePet
    doenca_atual: str | None = Field(None, max_length=255)

    @field_validator("doenca_atual", mode="before")
    @classmethod
    def limpar_doenca_atual(cls, valor: object) -> object:
        return _sem_espacos_nas_pontas(valor)

    @model_validator(mode="after")
    def validar_doenca_atual(self) -> "PetAtualizarStatusSaude":
        if self.status_saude == StatusSaudePet.EM_TRATAMENTO_MEDICO and not self.doenca_atual:
            raise ValueError(
                "doenca_atual e obrigatoria quando status_saude e 'em_tratamento_medico'"
            )
        return self


class EstadoSaudePet(BaseModel):
    """Retrato do status de saude, gravado na auditoria antes e depois de cada mudanca."""

    model_config = ConfigDict(from_attributes=True)

    status_saude: StatusSaudePet
    doenca_atual: str | None


class PetResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    especie: EspeciePet
    idade: int
    data_resgate: date
    status_saude: StatusSaudePet
    doenca_atual: str | None
    situacao_adocao: SituacaoAdocaoPet
    foto_url: str | None
    criado_em: datetime
    atualizado_em: datetime
