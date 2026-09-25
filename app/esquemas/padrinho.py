"""Schemas de Padrinho (RF09, RN08)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.esquemas.comuns import ValidacaoCpfNoCadastro


class PadrinhoBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150)
    cpf: str = Field(..., min_length=11, max_length=11)
    email: EmailStr
    telefone: str = Field(..., min_length=8, max_length=20)

    @field_validator("cpf")
    @classmethod
    def validar_cpf_numerico(cls, valor: str) -> str:
        if not valor.isdigit():
            raise ValueError("cpf deve conter apenas digitos (somente numeros, sem pontuacao)")
        return valor


class PadrinhoCriar(PadrinhoBase, ValidacaoCpfNoCadastro):
    pass


class PadrinhoAtualizar(BaseModel):
    nome: str | None = Field(None, min_length=2, max_length=150)
    email: EmailStr | None = None
    telefone: str | None = Field(None, min_length=8, max_length=20)


class PadrinhoResposta(PadrinhoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    criado_em: datetime
