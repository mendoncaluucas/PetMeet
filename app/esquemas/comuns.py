"""Schemas reutilizaveis entre os modulos (paginacao - RNF08; CPF - RN08)."""

import re
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, field_validator

T = TypeVar("T")


class PaginaResposta(BaseModel, Generic[T]):
    itens: list[T]
    total: int
    pagina: int
    tamanho_pagina: int


def _contrato_sem_nulo(esquema: dict[str, Any]) -> None:
    """Tira "null" das opcoes de tipo e o default null de cada campo do esquema publicado.

    Os campos sao declarados `X | None = None` so para o "nao enviado" funcionar; o
    contrato nao pode dizer que null e aceito, porque nao e.
    """
    for propriedade in esquema.get("properties", {}).values():
        opcoes = [opcao for opcao in propriedade.pop("anyOf", []) if opcao.get("type") != "null"]
        if len(opcoes) == 1:
            propriedade.update(opcoes[0])
        elif opcoes:
            propriedade["anyOf"] = opcoes
        if "default" in propriedade and propriedade["default"] is None:
            del propriedade["default"]


class AtualizacaoParcialSemNulo(BaseModel):
    """Base dos schemas de PATCH cujos campos sao todos NOT NULL no banco.

    None so vale como "campo nao enviado". Enviado como null, ia direto para a coluna e a
    atualizacao respondia 500 (DEF-14). O validador so roda para campos enviados, e o
    contrato publicado (OpenAPI) deixa de anunciar null.

    Nao use em schema com campo que pode ser limpo de proposito (enviado como null).
    """

    model_config = ConfigDict(json_schema_extra=_contrato_sem_nulo)

    @field_validator("*")
    @classmethod
    def recusar_nulo(cls, valor: Any) -> Any:
        if valor is None:
            raise ValueError("o campo nao aceita nulo; para nao alterar, deixe de envia-lo")
        return valor


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
