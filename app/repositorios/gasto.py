"""Acesso a dados de gastos (fase 3, H9)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload

from app.modelos.enums import CategoriaGasto
from app.modelos.gasto import Gasto

_COM_NOMES = (
    joinedload(Gasto.pet),
    joinedload(Gasto.registrado_por),
    joinedload(Gasto.estorno),
)


async def obter(sessao: AsyncSession, gasto_id: int) -> Gasto | None:
    consulta = (
        select(Gasto)
        .where(Gasto.id == gasto_id)
        .options(*_COM_NOMES)
        .execution_options(populate_existing=True)
    )
    return (await sessao.execute(consulta)).scalar_one_or_none()


async def obter_com_lock(sessao: AsyncSession, gasto_id: int) -> Gasto | None:
    """Sem os nomes: o Postgres nao trava o lado opcional de um LEFT JOIN."""
    consulta = (
        select(Gasto)
        .where(Gasto.id == gasto_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return (await sessao.execute(consulta)).scalar_one_or_none()


async def tem_estorno(sessao: AsyncSession, gasto_id: int) -> bool:
    consulta = select(Gasto.id).where(Gasto.estorno_de_id == gasto_id).limit(1)
    return (await sessao.execute(consulta)).first() is not None


async def listar(
    sessao: AsyncSession,
    pagina: int,
    tamanho_pagina: int,
    categoria: CategoriaGasto | None,
    pet_id: int | None,
) -> tuple[list[Gasto], int]:
    filtros = []
    if categoria is not None:
        filtros.append(Gasto.categoria == categoria)
    if pet_id is not None:
        filtros.append(Gasto.pet_id == pet_id)

    total = (
        await sessao.execute(select(func.count()).select_from(Gasto).where(*filtros))
    ).scalar_one()

    # Ordena pela data do original: o estorno aparece logo abaixo do lancamento que corrige
    # (H9.6), mesmo tendo data mais nova.
    original = aliased(Gasto)
    consulta = (
        select(Gasto)
        .outerjoin(original, original.id == Gasto.estorno_de_id)
        .where(*filtros)
        .options(*_COM_NOMES)
        .order_by(
            func.coalesce(original.data, Gasto.data).desc(),
            func.coalesce(Gasto.estorno_de_id, Gasto.id).desc(),
            Gasto.estorno_de_id.is_not(None),
        )
        .offset((pagina - 1) * tamanho_pagina)
        .limit(tamanho_pagina)
    )
    itens = (await sessao.execute(consulta)).scalars().unique().all()
    return list(itens), total
