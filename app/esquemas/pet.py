"""Schemas de Pet (RF01-05, RF16, RF18)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.esquemas.comuns import AtualizacaoParcialSemNulo
from app.modelos.enums import EspeciePet, SituacaoAdocaoPet, StatusSaudePet


class PetCriar(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    especie: EspeciePet
    idade: int = Field(..., ge=0, le=40)
    data_resgate: date
    status_saude: StatusSaudePet = StatusSaudePet.SAUDAVEL
    doenca_atual: str | None = Field(None, max_length=255)

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

    @model_validator(mode="after")
    def validar_doenca_atual(self) -> "PetAtualizarStatusSaude":
        if self.status_saude == StatusSaudePet.EM_TRATAMENTO_MEDICO and not self.doenca_atual:
            raise ValueError(
                "doenca_atual e obrigatoria quando status_saude e 'em_tratamento_medico'"
            )
        return self


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
