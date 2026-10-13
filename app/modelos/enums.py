"""Enumeracoes de dominio, compartilhadas entre modelos (SQLAlchemy) e schemas (Pydantic)."""

import enum

from sqlalchemy import Enum as EnumSQL


def coluna_enum(enum_cls: type[enum.Enum], nome_tipo_postgres: str) -> EnumSQL:
    """Cria o tipo de coluna Enum do SQLAlchemy para um Enum(str) de dominio.

    Por padrao, o SQLAlchemy grava o NOME do membro (ex.: "CACHORRO") em vez do
    seu VALOR (ex.: "cachorro") quando recebe uma classe Enum do Python. Como o
    tipo ENUM criado no Postgres (migration 0001) usa os valores em minusculo,
    e obrigatorio passar `values_callable` para gravar `.value`, senao qualquer
    INSERT/UPDATE falha com "invalid input value for enum ...".
    """
    return EnumSQL(
        enum_cls,
        name=nome_tipo_postgres,
        native_enum=True,
        values_callable=lambda cls: [membro.value for membro in cls],
    )


class PerfilUsuario(str, enum.Enum):
    ADMIN = "admin"
    VOLUNTARIO = "voluntario"
    VETERINARIO = "veterinario"


class EspeciePet(str, enum.Enum):
    CACHORRO = "cachorro"
    GATO = "gato"
    OUTRO = "outro"


class StatusSaudePet(str, enum.Enum):
    SAUDAVEL = "saudavel"
    EM_TRATAMENTO_MEDICO = "em_tratamento_medico"
    EM_RECUPERACAO = "em_recuperacao"


class SituacaoAdocaoPet(str, enum.Enum):
    DISPONIVEL = "disponivel"
    EM_PROCESSO_ADOCAO = "em_processo_adocao"
    ADOTADO = "adotado"


class StatusProcessoAdocao(str, enum.Enum):
    EM_ANALISE = "em_analise"
    APROVADO = "aprovado"
    FINALIZADO = "finalizado"
    CANCELADO = "cancelado"


class FrequenciaContribuicao(str, enum.Enum):
    PONTUAL = "pontual"
    RECORRENTE = "recorrente"
