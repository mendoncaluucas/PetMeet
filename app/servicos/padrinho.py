"""Regras de negocio de Padrinho (RF09-11)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import RecursoNaoEncontradoError, RegraNegocioError
from app.esquemas.padrinho import PadrinhoAtualizar, PadrinhoCriar
from app.modelos.padrinho import Padrinho
from app.repositorios import padrinho as repo_padrinho
from app.servicos.unicidade import gravar_sem_duplicar


async def criar_padrinho(sessao: AsyncSession, dados: PadrinhoCriar) -> Padrinho:
    duplicado = f"Ja existe um padrinho cadastrado com o cpf {dados.cpf}."
    if await repo_padrinho.obter_por_cpf(sessao, dados.cpf) is not None:
        raise RegraNegocioError(duplicado)

    padrinho = Padrinho(**dados.model_dump())
    return await gravar_sem_duplicar(sessao, repo_padrinho.criar(sessao, padrinho), duplicado)


async def obter_padrinho_ou_falhar(sessao: AsyncSession, padrinho_id: int) -> Padrinho:
    padrinho = await repo_padrinho.obter_por_id(sessao, padrinho_id)
    if padrinho is None:
        raise RecursoNaoEncontradoError(f"Padrinho {padrinho_id} nao encontrado.")
    return padrinho


async def listar_padrinhos(
    sessao: AsyncSession, pagina: int, tamanho_pagina: int
) -> tuple[list[Padrinho], int]:
    return await repo_padrinho.listar(sessao, pagina, tamanho_pagina)


async def atualizar_padrinho(
    sessao: AsyncSession, padrinho_id: int, dados: PadrinhoAtualizar
) -> Padrinho:
    padrinho = await obter_padrinho_ou_falhar(sessao, padrinho_id)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(padrinho, campo, valor)
    return await repo_padrinho.salvar(sessao, padrinho)
