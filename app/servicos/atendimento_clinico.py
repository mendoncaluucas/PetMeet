"""Regras da ficha clinica (fase 2, H3; decisoes D7 e D8)."""

from datetime import date

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import RecursoNaoEncontradoError, RegraNegocioError
from app.esquemas.atendimento_clinico import AtendimentoAnular, AtendimentoCriar
from app.modelos.atendimento_clinico import AtendimentoClinico
from app.modelos.usuario import Usuario
from app.repositorios import atendimento_clinico as repo_atendimento
from app.repositorios import pet as repo_pet


async def registrar(
    sessao: AsyncSession, pet_id: int, dados: AtendimentoCriar, veterinario: Usuario, hoje: date
) -> AtendimentoClinico:
    """`hoje` e o dia em Brasilia (hoje_na_ong): em UTC, depois das 21h ja seria amanha."""
    if await repo_pet.obter_por_id(sessao, pet_id) is None:
        raise RecursoNaoEncontradoError(f"Pet {pet_id} nao encontrado.")
    if dados.data_atendimento > hoje:
        raise RegraNegocioError("A data do atendimento nao pode estar no futuro.")

    # Registrar nao mexe no status de saude: a alta e uma acao separada (H2).
    atendimento = AtendimentoClinico(
        pet_id=pet_id,
        veterinario_id=veterinario.id,
        data_atendimento=dados.data_atendimento,
        anamnese=dados.anamnese,
        diagnostico=dados.diagnostico,
        conduta=dados.conduta,
    )
    sessao.add(atendimento)
    await sessao.commit()
    return await _com_nomes(sessao, atendimento.id)


async def listar_do_pet(
    sessao: AsyncSession, pet_id: int, pagina: int, tamanho_pagina: int
) -> tuple[list[AtendimentoClinico], int]:
    if await repo_pet.obter_por_id(sessao, pet_id) is None:
        raise RecursoNaoEncontradoError(f"Pet {pet_id} nao encontrado.")
    return await repo_atendimento.listar_do_pet(sessao, pet_id, pagina, tamanho_pagina)


async def anular(
    sessao: AsyncSession, atendimento_id: int, dados: AtendimentoAnular, veterinario: Usuario
) -> AtendimentoClinico:
    # Trava a linha: duas anulacoes ao mesmo tempo nao podem as duas passar pelo "ja anulado".
    atendimento = await repo_atendimento.obter_por_id_com_lock(sessao, atendimento_id)
    if atendimento is None:
        raise RecursoNaoEncontradoError(f"Atendimento {atendimento_id} nao encontrado.")
    if atendimento.anulado_em is not None:
        raise RegraNegocioError("Este atendimento ja foi anulado.")

    # Relogio do banco, o mesmo do criado_em: anulado nunca aparece antes de criado.
    atendimento.anulado_em = func.now()
    atendimento.anulado_por_id = veterinario.id
    atendimento.motivo_anulacao = dados.motivo
    await sessao.commit()
    return await _com_nomes(sessao, atendimento.id)


async def _com_nomes(sessao: AsyncSession, atendimento_id: int) -> AtendimentoClinico:
    atendimento = await repo_atendimento.obter_por_id(sessao, atendimento_id)
    assert atendimento is not None  # acabou de ser gravado nesta sessao
    return atendimento
