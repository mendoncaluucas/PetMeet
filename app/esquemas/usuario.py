"""Schemas do usuario da equipe da ONG (RF20, RF21)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.seguranca import LIMITE_BYTES_SENHA, senha_cabe_no_bcrypt
from app.modelos.enums import PerfilUsuario


class UsuarioCriar(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    senha: str = Field(..., min_length=8, max_length=LIMITE_BYTES_SENHA)
    perfil: PerfilUsuario

    @field_validator("senha")
    @classmethod
    def validar_senha_em_bytes(cls, valor: str) -> str:
        # max_length conta caracteres; o limite real do bcrypt e em bytes.
        if not senha_cabe_no_bcrypt(valor):
            raise ValueError(
                f"senha deve ter no maximo {LIMITE_BYTES_SENHA} bytes "
                "(letras acentuadas contam como 2)"
            )
        return valor


class UsuarioResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: EmailStr
    perfil: PerfilUsuario
    ativo: bool
    criado_em: datetime
