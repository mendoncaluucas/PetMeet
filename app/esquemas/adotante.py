"""Schemas de Adotante (RF06, RF07, RN08)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.esquemas.comuns import ValidacaoCpfNoCadastro


class AdotanteBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150)
    cpf: str = Field(..., min_length=11, max_length=11)
    email: EmailStr
    telefone: str = Field(..., min_length=8, max_length=20)
    endereco: str = Field(..., min_length=5, max_length=255)

    @field_validator("cpf")
    @classmethod
    def validar_cpf_numerico(cls, valor: str) -> str:
        if not valor.isdigit():
            raise ValueError("cpf deve conter apenas digitos (somente numeros, sem pontuacao)")
        return valor


class AdotanteCriar(AdotanteBase, ValidacaoCpfNoCadastro):
    pass


class AdotanteAtualizar(BaseModel):
    nome: str | None = Field(None, min_length=2, max_length=150)
    email: EmailStr | None = None
    telefone: str | None = Field(None, min_length=8, max_length=20)
    endereco: str | None = Field(None, min_length=5, max_length=255)
    # False inativa, True reativa (DEF-13).
    ativo: bool | None = None

    @field_validator("*")
    @classmethod
    def recusar_nulo(cls, valor: object) -> object:
        # None so vale como "campo nao enviado". Enviado como null, ia direto para uma
        # coluna NOT NULL e a atualizacao respondia 500 (DEF-14).
        if valor is None:
            raise ValueError("o campo nao aceita nulo; para nao alterar, deixe de envia-lo")
        return valor


class AdotanteResposta(AdotanteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ativo: bool
    criado_em: datetime
