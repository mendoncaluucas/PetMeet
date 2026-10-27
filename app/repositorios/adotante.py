"""Acesso a dados de Adotante (RF06-08)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.adotante import Adotante
from app.modelos.processo_adocao import ProcessoAdocao


async def criar(sessao: AsyncSession, adotante: Adotante) -> Adotante:
    sessao.add(adotante)
    await sessao.commit()
    await sessao.refresh(adotante)
    return adotante


async def obter_por_id(sessao: AsyncSession, adotante_id: int) -> Adotante | None:
    return await sessao.get(Adotante, adotante_id)


async def obter_por_id_com_lock(
    sessao: AsyncSession, adotante_id: int, *, compartilhado: bool = False
) -> Adotante | None:
    """SELECT ... FOR UPDATE, ou FOR SHARE com `compartilhado`.

    A exclusao trava com FOR UPDATE; a abertura de processo, com FOR SHARE. Uma espera a
    outra, e quem chega depois ve o resultado de quem chegou antes. populate_existing
    garante o valor da linha travada mesmo se o adotante ja estava carregado na sessao.
    """
    consulta = (
        select(Adotante)
        .where(Adotante.id == adotante_id)
        .with_for_update(read=compartilhado)
        .execution_options(populate_existing=True)
    )
    return (await sessao.execute(consulta)).scalar_one_or_none()


async def tem_processo(sessao: AsyncSession, adotante_id: int) -> bool:
    consulta = select(ProcessoAdocao.id).where(ProcessoAdocao.adotante_id == adotante_id).limit(1)
    return (await sessao.execute(consulta)).first() is not None


async def excluir(sessao: AsyncSession, adotante: Adotante) -> None:
    await sessao.delete(adotante)
    await sessao.commit()


async def obter_por_cpf(sessao: AsyncSession, cpf: str) -> Adotante | None:
    resultado = await sessao.execute(select(Adotante).where(Adotante.cpf == cpf))
    return resultado.scalar_one_or_none()


async def listar(
    sessao: AsyncSession, pagina: int, tamanho_pagina: int, incluir_inativos: bool = False
) -> tuple[list[Adotante], int]:
    filtro = [] if incluir_inativos else [Adotante.ativo.is_(True)]
    total = (
        await sessao.execute(select(func.count()).select_from(Adotante).where(*filtro))
    ).scalar_one()
    consulta = (
        select(Adotante)
        .where(*filtro)
        .order_by(Adotante.criado_em.desc())
        .offset((pagina - 1) * tamanho_pagina)
        .limit(tamanho_pagina)
    )
    itens = (await sessao.execute(consulta)).scalars().all()
    return list(itens), total


async def salvar(sessao: AsyncSession, adotante: Adotante) -> Adotante:
    await sessao.commit()
    await sessao.refresh(adotante)
    return adotante
