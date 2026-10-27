"""Acesso a dados da ficha clinica (fase 2, H3)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.modelos.atendimento_clinico import AtendimentoClinico

# Os nomes de quem registrou e de quem anulou vao na resposta.
_COM_NOMES = (
    joinedload(AtendimentoClinico.veterinario),
    joinedload(AtendimentoClinico.anulado_por),
)


async def obter_por_id(sessao: AsyncSession, atendimento_id: int) -> AtendimentoClinico | None:
    consulta = (
        select(AtendimentoClinico)
        .where(AtendimentoClinico.id == atendimento_id)
        .options(*_COM_NOMES)
        .execution_options(populate_existing=True)
    )
    return (await sessao.execute(consulta)).scalar_one_or_none()


async def obter_por_id_com_lock(
    sessao: AsyncSession, atendimento_id: int
) -> AtendimentoClinico | None:
    """SELECT ... FOR UPDATE sem os nomes: o Postgres nao trava o lado opcional de um
    LEFT JOIN, e quem anulou e opcional."""
    consulta = (
        select(AtendimentoClinico)
        .where(AtendimentoClinico.id == atendimento_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return (await sessao.execute(consulta)).scalar_one_or_none()


async def listar_do_pet(
    sessao: AsyncSession, pet_id: int, pagina: int, tamanho_pagina: int
) -> tuple[list[AtendimentoClinico], int]:
    filtro = AtendimentoClinico.pet_id == pet_id
    total = (
        await sessao.execute(select(func.count()).select_from(AtendimentoClinico).where(filtro))
    ).scalar_one()

    # Mais recente primeiro; no mesmo dia, o registrado por ultimo.
    consulta = (
        select(AtendimentoClinico)
        .where(filtro)
        .options(*_COM_NOMES)
        .order_by(AtendimentoClinico.data_atendimento.desc(), AtendimentoClinico.id.desc())
        .offset((pagina - 1) * tamanho_pagina)
        .limit(tamanho_pagina)
    )
    itens = (await sessao.execute(consulta)).scalars().all()
    return list(itens), total
