"""Regras de negocio de Adotante (RF06-08)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import RecursoNaoEncontradoError, RegraNegocioError
from app.esquemas.adotante import AdotanteAtualizar, AdotanteCriar
from app.modelos.adotante import Adotante
from app.repositorios import adotante as repo_adotante
from app.servicos.unicidade import gravar_sem_duplicar


async def criar_adotante(sessao: AsyncSession, dados: AdotanteCriar) -> Adotante:
    duplicado = f"Ja existe um adotante cadastrado com o cpf {dados.cpf}."
    if await repo_adotante.obter_por_cpf(sessao, dados.cpf) is not None:
        raise RegraNegocioError(duplicado)

    adotante = Adotante(**dados.model_dump())
    return await gravar_sem_duplicar(sessao, repo_adotante.criar(sessao, adotante), duplicado)


async def obter_adotante_ou_falhar(sessao: AsyncSession, adotante_id: int) -> Adotante:
    adotante = await repo_adotante.obter_por_id(sessao, adotante_id)
    if adotante is None:
        raise RecursoNaoEncontradoError(f"Adotante {adotante_id} nao encontrado.")
    return adotante


async def listar_adotantes(
    sessao: AsyncSession, pagina: int, tamanho_pagina: int
) -> tuple[list[Adotante], int]:
    return await repo_adotante.listar(sessao, pagina, tamanho_pagina)


async def atualizar_adotante(
    sessao: AsyncSession, adotante_id: int, dados: AdotanteAtualizar
) -> Adotante:
    adotante = await obter_adotante_ou_falhar(sessao, adotante_id)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(adotante, campo, valor)
    return await repo_adotante.salvar(sessao, adotante)
