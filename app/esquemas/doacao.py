"""Schemas de doacao (RF12, RF13, RN05)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.esquemas.comuns import IdNoCorpo
from app.modelos.enums import FrequenciaContribuicao


class DoacaoCriar(BaseModel):
    padrinho_id: IdNoCorpo | None = None
    doador_nome: str | None = Field(None, max_length=150)
    # Numeric(10, 2) no banco: ate 99.999.999,99. Acima disso o banco recusava com 500, e
    # com mais de 2 casas arredondava calado (R$ 10,123 virava 10,12) -- DEF-15.
    valor: Decimal = Field(
        ...,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Valor da doacao, maior que zero (RN05), com ate 2 casas decimais",
    )
    data: date
    tipo: FrequenciaContribuicao

    @model_validator(mode="after")
    def validar_origem_doacao(self) -> "DoacaoCriar":
        # A doacao precisa ser rastreavel a alguem: um padrinho cadastrado ou um doador avulso.
        if self.padrinho_id is None and not self.doador_nome:
            raise ValueError("informe padrinho_id ou doador_nome")
        return self


class DoacaoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    padrinho_id: int | None
    doador_nome: str | None
    valor: Decimal
    data: date
    tipo: FrequenciaContribuicao
    criado_em: datetime
