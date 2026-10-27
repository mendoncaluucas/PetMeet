"""Schemas da ficha clinica (fase 2, H3)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _aparar(valor: object) -> object:
    """Texto so com espacos conta como vazio: "   " nao vale como anamnese nem como motivo."""
    if isinstance(valor, str):
        return valor.strip() or None
    return valor


class AtendimentoCriar(BaseModel):
    # O veterinario vem do login, nunca do corpo: campo extra e ignorado.
    data_atendimento: date
    anamnese: str = Field(..., min_length=1, max_length=5000)
    diagnostico: str | None = Field(None, max_length=2000)
    conduta: str | None = Field(None, max_length=2000)

    @field_validator("anamnese", "diagnostico", "conduta", mode="before")
    @classmethod
    def aparar_textos(cls, valor: object) -> object:
        return _aparar(valor)


class AtendimentoAnular(BaseModel):
    motivo: str = Field(..., min_length=1, max_length=500)

    @field_validator("motivo", mode="before")
    @classmethod
    def aparar_motivo(cls, valor: object) -> object:
        return _aparar(valor)


class AtendimentoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pet_id: int
    data_atendimento: date
    anamnese: str
    diagnostico: str | None
    conduta: str | None
    veterinario_id: int
    veterinario_nome: str
    criado_em: datetime
    anulado_em: datetime | None
    anulado_por_nome: str | None
    motivo_anulacao: str | None
