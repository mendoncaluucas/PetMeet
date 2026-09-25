"""Schemas reutilizaveis entre os modulos (paginacao - RNF08; CPF - RN08)."""

import re
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, field_validator

T = TypeVar("T")


class PaginaResposta(BaseModel, Generic[T]):
    itens: list[T]
    total: int
    pagina: int
    tamanho_pagina: int


def normalizar_cpf(valor: str) -> str:
    """Tira pontuacao e espacos: '529.982.247-25' -> '52998224725'."""
    return re.sub(r"[.\-\s]", "", valor)


def cpf_valido(cpf: str) -> bool:
    """Confere os dois digitos verificadores. Sequencias como 111.111.111-11 passam na
    conta, mas nao sao CPF emitido, e sao recusadas."""
    if len(cpf) != 11 or not cpf.isdigit() or cpf == cpf[0] * 11:
        return False
    for tamanho in (9, 10):
        pesos = range(tamanho + 1, 1, -1)
        soma = sum(int(digito) * peso for digito, peso in zip(cpf[:tamanho], pesos, strict=True))
        if soma * 10 % 11 % 10 != int(cpf[tamanho]):
            return False
    return True


class ValidacaoCpfNoCadastro(BaseModel):
    """Aceita CPF com pontuacao e confere os digitos verificadores.

    Entra so nos schemas de criacao. Os de resposta nao podem herdar esta regra: o
    validador rodaria tambem na leitura, e qualquer CPF ja gravado fora dela derrubaria
    a listagem inteira com 500.
    """

    @field_validator("cpf", mode="before", check_fields=False)
    @classmethod
    def normalizar(cls, valor: Any) -> Any:
        return normalizar_cpf(valor) if isinstance(valor, str) else valor

    @field_validator("cpf", check_fields=False)
    @classmethod
    def conferir_digitos(cls, valor: str) -> str:
        if not cpf_valido(valor):
            raise ValueError("cpf invalido: os digitos verificadores nao conferem")
        return valor
