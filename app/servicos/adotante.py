"""Regras de negocio de Adotante (RF06-08)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import ConflitoError, RecursoNaoEncontradoError, RegraNegocioError
from app.esquemas.adotante import AdotanteAtualizar, AdotanteCriar
from app.modelos.adotante import Adotante
from app.repositorios import adotante as repo_adotante
from app.servicos.unicidade import gravar_sem_duplicar


async def criar_adotante(sessao: AsyncSession, dados: AdotanteCriar) -> Adotante:
    duplicado = f"Ja existe um adotante cadastrado com o cpf {dados.cpf}."
    existente = await repo_adotante.obter_por_cpf(sessao, dados.cpf)
    if existente is not None and not existente.ativo:
        raise RegraNegocioError(
            f"Ja existe um adotante inativo com o cpf {dados.cpf}: reative o cadastro dele."
        )
    if existente is not None:
        raise RegraNegocioError(duplicado)

    adotante = Adotante(**dados.model_dump())
    return await gravar_sem_duplicar(sessao, repo_adotante.criar(sessao, adotante), duplicado)


async def obter_adotante_ou_falhar(sessao: AsyncSession, adotante_id: int) -> Adotante:
    adotante = await repo_adotante.obter_por_id(sessao, adotante_id)
    if adotante is None:
        raise RecursoNaoEncontradoError(f"Adotante {adotante_id} nao encontrado.")
    return adotante


async def listar_adotantes(
    sessao: AsyncSession, pagina: int, tamanho_pagina: int, incluir_inativos: bool = False
) -> tuple[list[Adotante], int]:
    return await repo_adotante.listar(sessao, pagina, tamanho_pagina, incluir_inativos)


async def atualizar_adotante(
    sessao: AsyncSession, adotante_id: int, dados: AdotanteAtualizar
) -> Adotante:
    # Trava como a exclusao trava: se ela chegou antes, aqui o adotante ja nao existe
    # (404). Sem a trava, o UPDATE nao achava a linha e respondia 500.
    adotante = await repo_adotante.obter_por_id_com_lock(sessao, adotante_id)
    if adotante is None:
        raise RecursoNaoEncontradoError(f"Adotante {adotante_id} nao encontrado.")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(adotante, campo, valor)
    return await repo_adotante.salvar(sessao, adotante)


async def excluir_adotante(sessao: AsyncSession, adotante_id: int) -> None:
    """Exclui so quem nunca teve processo de adocao (DEF-13).

    Trava o adotante antes de conferir os processos. A abertura de processo trava o
    mesmo adotante (FOR SHARE), entao uma espera a outra: se a abertura chegou antes, a
    exclusao ve o processo e recusa; se a exclusao chegou antes, a abertura encontra o
    adotante excluido.
    """
    adotante = await repo_adotante.obter_por_id_com_lock(sessao, adotante_id)
    if adotante is None:
        raise RecursoNaoEncontradoError(f"Adotante {adotante_id} nao encontrado.")
    if await repo_adotante.tem_processo(sessao, adotante_id):
        raise ConflitoError(
            "Este adotante tem processo de adocao no historico e nao pode ser excluido: "
            "inative o cadastro."
        )
    await repo_adotante.excluir(sessao, adotante)
