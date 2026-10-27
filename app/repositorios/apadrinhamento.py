"""Acesso a dados do apadrinhamento (fase 3, H7)."""

from datetime import date

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.modelos.apadrinhamento import Apadrinhamento

_COM_NOMES = (joinedload(Apadrinhamento.padrinho), joinedload(Apadrinhamento.pet))


async def obter(sessao: AsyncSession, apadrinhamento_id: int) -> Apadrinhamento | None:
    consulta = (
        select(Apadrinhamento)
        .where(Apadrinhamento.id == apadrinhamento_id)
        .options(*_COM_NOMES)
        .execution_options(populate_existing=True)
    )
    return (await sessao.execute(consulta)).scalar_one_or_none()


async def obter_com_lock(sessao: AsyncSession, apadrinhamento_id: int) -> Apadrinhamento | None:
    consulta = (
        select(Apadrinhamento)
        .where(Apadrinhamento.id == apadrinhamento_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return (await sessao.execute(consulta)).scalar_one_or_none()


async def existe_ativo(sessao: AsyncSession, padrinho_id: int, pet_id: int) -> bool:
    consulta = select(Apadrinhamento.id).where(
        Apadrinhamento.padrinho_id == padrinho_id,
        Apadrinhamento.pet_id == pet_id,
        Apadrinhamento.data_fim.is_(None),
    )
    return (await sessao.execute(consulta.limit(1))).first() is not None


async def listar(
    sessao: AsyncSession,
    pagina: int,
    tamanho_pagina: int,
    padrinho_id: int | None,
    pet_id: int | None,
    incluir_encerrados: bool,
) -> tuple[list[Apadrinhamento], int]:
    filtros = []
    if padrinho_id is not None:
        filtros.append(Apadrinhamento.padrinho_id == padrinho_id)
    if pet_id is not None:
        filtros.append(Apadrinhamento.pet_id == pet_id)
    if not incluir_encerrados:
        filtros.append(Apadrinhamento.data_fim.is_(None))

    total = (
        await sessao.execute(select(func.count()).select_from(Apadrinhamento).where(*filtros))
    ).scalar_one()
    # Ativos primeiro; depois os mais recentes.
    consulta = (
        select(Apadrinhamento)
        .where(*filtros)
        .options(*_COM_NOMES)
        .order_by(
            Apadrinhamento.data_fim.is_not(None),
            Apadrinhamento.data_inicio.desc(),
            Apadrinhamento.id.desc(),
        )
        .offset((pagina - 1) * tamanho_pagina)
        .limit(tamanho_pagina)
    )
    itens = (await sessao.execute(consulta)).scalars().all()
    return list(itens), total


async def contar_ativos_do_pet(sessao: AsyncSession, pet_id: int) -> int:
    consulta = select(func.count()).where(
        Apadrinhamento.pet_id == pet_id, Apadrinhamento.data_fim.is_(None)
    )
    return (await sessao.execute(consulta)).scalar_one()


async def encerrar_ativos_do_pet(sessao: AsyncSession, pet_id: int, data_fim: date) -> int:
    """Encerra os ativos do pet na transacao de quem chama (D12). Devolve quantos."""
    resultado = await sessao.execute(
        update(Apadrinhamento)
        .where(Apadrinhamento.pet_id == pet_id, Apadrinhamento.data_fim.is_(None))
        # data_inicio no futuro nao existe (o servico recusa), mas o CHECK do banco exige
        # fim >= inicio: GREATEST garante que o encerramento nunca quebra a finalizacao.
        .values(data_fim=func.greatest(Apadrinhamento.data_inicio, data_fim))
        .returning(Apadrinhamento.id)
        .execution_options(synchronize_session=False)
    )
    return len(resultado.all())
