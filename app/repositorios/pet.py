"""Acesso a dados de Pet (RF01-05)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.enums import EspeciePet, SituacaoAdocaoPet, StatusSaudePet
from app.modelos.pet import Pet


async def criar(sessao: AsyncSession, pet: Pet) -> Pet:
    sessao.add(pet)
    await sessao.commit()
    await sessao.refresh(pet)
    return pet


async def obter_por_id(sessao: AsyncSession, pet_id: int) -> Pet | None:
    return await sessao.get(Pet, pet_id)


async def obter_por_id_com_lock(sessao: AsyncSession, pet_id: int) -> Pet | None:
    """SELECT ... FOR UPDATE: trava a linha do pet durante uma transacao (RNF18).

    populate_existing garante que o objeto devolvido reflete a linha travada, mesmo
    que o pet ja estivesse carregado na sessao antes da trava.
    """
    consulta = (
        select(Pet)
        .where(Pet.id == pet_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    resultado = await sessao.execute(consulta)
    return resultado.scalar_one_or_none()


async def listar(
    sessao: AsyncSession,
    pagina: int,
    tamanho_pagina: int,
    especie: EspeciePet | None = None,
    status_saude: StatusSaudePet | None = None,
    situacao_adocao: SituacaoAdocaoPet | None = None,
) -> tuple[list[Pet], int]:
    consulta = select(Pet)
    if especie is not None:
        consulta = consulta.where(Pet.especie == especie)
    if status_saude is not None:
        consulta = consulta.where(Pet.status_saude == status_saude)
    if situacao_adocao is not None:
        consulta = consulta.where(Pet.situacao_adocao == situacao_adocao)

    total = (
        await sessao.execute(select(func.count()).select_from(consulta.subquery()))
    ).scalar_one()

    consulta = (
        consulta.order_by(Pet.criado_em.desc())
        .offset((pagina - 1) * tamanho_pagina)
        .limit(tamanho_pagina)
    )
    itens = (await sessao.execute(consulta)).scalars().all()
    return list(itens), total


async def salvar(sessao: AsyncSession, pet: Pet) -> Pet:
    await sessao.commit()
    await sessao.refresh(pet)
    return pet
