"""Acesso a dados de Doacao (RF12, RF13; estornos na fase 3, H9)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload

from app.modelos.doacao import Doacao

_COM_NOMES = (joinedload(Doacao.registrado_por), joinedload(Doacao.estorno))


async def obter(sessao: AsyncSession, doacao_id: int) -> Doacao | None:
    consulta = (
        select(Doacao)
        .where(Doacao.id == doacao_id)
        .options(*_COM_NOMES)
        .execution_options(populate_existing=True)
    )
    return (await sessao.execute(consulta)).scalar_one_or_none()


async def obter_com_lock(sessao: AsyncSession, doacao_id: int) -> Doacao | None:
    """Sem os nomes: o Postgres nao trava o lado opcional de um LEFT JOIN."""
    consulta = (
        select(Doacao)
        .where(Doacao.id == doacao_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return (await sessao.execute(consulta)).scalar_one_or_none()


async def tem_estorno(sessao: AsyncSession, doacao_id: int) -> bool:
    consulta = select(Doacao.id).where(Doacao.estorno_de_id == doacao_id).limit(1)
    return (await sessao.execute(consulta)).first() is not None


async def listar(
    sessao: AsyncSession, pagina: int, tamanho_pagina: int, padrinho_id: int | None = None
) -> tuple[list[Doacao], int]:
    filtros = [] if padrinho_id is None else [Doacao.padrinho_id == padrinho_id]

    total = (
        await sessao.execute(select(func.count()).select_from(Doacao).where(*filtros))
    ).scalar_one()

    # Ordena pela data da doacao original: o estorno aparece logo abaixo dela (H9.6).
    original = aliased(Doacao)
    consulta = (
        select(Doacao)
        .outerjoin(original, original.id == Doacao.estorno_de_id)
        .where(*filtros)
        .options(*_COM_NOMES)
        .order_by(
            func.coalesce(original.data, Doacao.data).desc(),
            func.coalesce(Doacao.estorno_de_id, Doacao.id).desc(),
            Doacao.estorno_de_id.is_not(None),
        )
        .offset((pagina - 1) * tamanho_pagina)
        .limit(tamanho_pagina)
    )
    itens = (await sessao.execute(consulta)).scalars().unique().all()
    return list(itens), total
