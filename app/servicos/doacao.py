"""Regras de negocio de Doacao (RF12, RF13, RN05)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import RecursoNaoEncontradoError
from app.esquemas.doacao import DoacaoCriar
from app.modelos.doacao import Doacao
from app.repositorios import doacao as repo_doacao
from app.repositorios import padrinho as repo_padrinho
from app.repositorios import pet as repo_pet


async def criar_doacao(sessao: AsyncSession, dados: DoacaoCriar) -> Doacao:
    if dados.padrinho_id is not None:
        padrinho = await repo_padrinho.obter_por_id(sessao, dados.padrinho_id)
        if padrinho is None:
            raise RecursoNaoEncontradoError(f"Padrinho {dados.padrinho_id} nao encontrado.")
    if dados.pet_id is not None and await repo_pet.obter_por_id(sessao, dados.pet_id) is None:
        raise RecursoNaoEncontradoError(f"Pet {dados.pet_id} nao encontrado.")

    # RN05 (valor > 0) ja e garantida pelo schema (Field(gt=0)) e pelo CHECK constraint no banco.
    doacao = Doacao(**dados.model_dump())
    return await repo_doacao.criar(sessao, doacao)


async def listar_doacoes(
    sessao: AsyncSession, pagina: int, tamanho_pagina: int, padrinho_id: int | None = None
) -> tuple[list[Doacao], int]:
    return await repo_doacao.listar(sessao, pagina, tamanho_pagina, padrinho_id)
