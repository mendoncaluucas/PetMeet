"""Consultas do resumo do Painel: tudo agregado no banco, sem baixar listagens inteiras."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Row, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.adotante import Adotante
from app.modelos.doacao import Doacao
from app.modelos.enums import SituacaoAdocaoPet, StatusProcessoAdocao, StatusSaudePet
from app.modelos.pet import Pet
from app.modelos.processo_adocao import ProcessoAdocao

_ATIVOS = (StatusProcessoAdocao.EM_ANALISE, StatusProcessoAdocao.APROVADO)


async def contar_pets(sessao: AsyncSession) -> tuple[int, int, int]:
    """Total, disponiveis para adocao e em tratamento medico."""
    consulta = select(
        func.count(),
        func.count().filter(Pet.situacao_adocao == SituacaoAdocaoPet.DISPONIVEL),
        func.count().filter(Pet.status_saude == StatusSaudePet.EM_TRATAMENTO_MEDICO),
    ).select_from(Pet)
    total, disponiveis, em_tratamento = (await sessao.execute(consulta)).one()
    return total, disponiveis, em_tratamento


async def contar_processos_ativos(sessao: AsyncSession) -> tuple[int, int]:
    """Em andamento (em analise ou aprovado) e, desses, aprovados aguardando finalizacao."""
    consulta = select(
        func.count(),
        func.count().filter(ProcessoAdocao.status == StatusProcessoAdocao.APROVADO),
    ).where(ProcessoAdocao.status.in_(_ATIVOS))
    em_andamento, aguardando = (await sessao.execute(consulta)).one()
    return em_andamento, aguardando


async def somar_doacoes(sessao: AsyncSession, inicio: date, fim: date) -> tuple[Decimal, int]:
    """Soma e quantidade de doacoes com data em [inicio, fim)."""
    consulta = select(func.coalesce(func.sum(Doacao.valor), 0), func.count()).where(
        Doacao.data >= inicio, Doacao.data < fim
    )
    total, quantidade = (await sessao.execute(consulta)).one()
    return Decimal(total), quantidade


async def pets_em_tratamento(sessao: AsyncSession, limite: int) -> list[Pet]:
    consulta = (
        select(Pet)
        .where(Pet.status_saude == StatusSaudePet.EM_TRATAMENTO_MEDICO)
        .order_by(Pet.data_resgate, Pet.id)
        .limit(limite)
    )
    return list((await sessao.execute(consulta)).scalars())


async def pets_esperando_ha_mais_tempo(sessao: AsyncSession, limite: int) -> list[Pet]:
    consulta = (
        select(Pet)
        .where(Pet.situacao_adocao == SituacaoAdocaoPet.DISPONIVEL)
        .order_by(Pet.data_resgate, Pet.id)
        .limit(limite)
    )
    return list((await sessao.execute(consulta)).scalars())


async def processos_em_andamento(sessao: AsyncSession, limite: int) -> list[Row]:
    consulta = (
        select(
            ProcessoAdocao.id,
            ProcessoAdocao.status,
            ProcessoAdocao.pet_id,
            Pet.nome.label("pet_nome"),
            Pet.status_saude.label("pet_status_saude"),
            ProcessoAdocao.adotante_id,
            Adotante.nome.label("adotante_nome"),
        )
        .join(Pet, Pet.id == ProcessoAdocao.pet_id)
        .join(Adotante, Adotante.id == ProcessoAdocao.adotante_id)
        .where(ProcessoAdocao.status.in_(_ATIVOS))
        .order_by(ProcessoAdocao.criado_em.desc())
        .limit(limite)
    )
    return list((await sessao.execute(consulta)).all())
