"""Consultas do portal de prestacao de contas (fase 3, H11): tudo somado no banco.

Os estornos sao lancamentos negativos com a data do dia da correcao (D13): somar todas as
linhas por data ja da o resultado certo, e o total de um mes fechado nao muda depois.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import DateTime, Label, Numeric, Row, String, cast, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.modelos.doacao import Doacao
from app.modelos.gasto import Gasto
from app.modelos.pet import Pet

_ZERO = cast(literal(0), Numeric(12, 2))


def _mes(coluna: InstrumentedAttribute[date]) -> Label[str]:
    """Mes da data, como "2026-10". A data ja e o dia de Brasilia (hoje_na_ong).

    O cast e para `timestamp` sem fuso: sem ele, o Postgres converte a data para
    `timestamptz`, e o resultado passa a depender do fuso da sessao do banco.
    """
    return func.to_char(cast(coluna, DateTime()), "YYYY-MM", type_=String).label("mes")


async def saldo_antes_de(sessao: AsyncSession, inicio: date) -> Decimal:
    """Arrecadado menos gasto de tudo o que foi lancado antes de `inicio`."""
    doado = select(func.coalesce(func.sum(Doacao.valor), 0)).where(Doacao.data < inicio)
    gasto = select(func.coalesce(func.sum(Gasto.valor), 0)).where(Gasto.data < inicio)
    saldo = select(doado.scalar_subquery() - gasto.scalar_subquery())
    return Decimal((await sessao.execute(saldo)).scalar_one())


async def arrecadado_por_mes(sessao: AsyncSession, inicio: date, fim: date) -> dict[str, Decimal]:
    mes = _mes(Doacao.data)
    consulta = (
        select(mes, func.sum(Doacao.valor))
        .where(Doacao.data >= inicio, Doacao.data < fim)
        .group_by(mes)
    )
    return {linha[0]: Decimal(linha[1]) for linha in await sessao.execute(consulta)}


async def gasto_por_mes_e_categoria(sessao: AsyncSession, inicio: date, fim: date) -> list[Row]:
    """(mes, categoria, total), do maior gasto para o menor dentro de cada mes."""
    mes = _mes(Gasto.data)
    total = func.sum(Gasto.valor).label("total")
    consulta = (
        select(mes, Gasto.categoria, total)
        .where(Gasto.data >= inicio, Gasto.data < fim)
        .group_by(mes, Gasto.categoria)
        .order_by(mes, total.desc(), Gasto.categoria)
    )
    return list((await sessao.execute(consulta)).all())


async def movimento_por_pet(sessao: AsyncSession, inicio: date, fim: date) -> list[Row]:
    """(pet_id, nome, arrecadado, gasto) dos pets com algum lancamento no periodo."""
    lancamentos = union_all(
        select(Doacao.pet_id, Doacao.valor.label("arrecadado"), _ZERO.label("gasto")).where(
            Doacao.pet_id.is_not(None), Doacao.data >= inicio, Doacao.data < fim
        ),
        select(Gasto.pet_id, _ZERO, Gasto.valor).where(
            Gasto.pet_id.is_not(None), Gasto.data >= inicio, Gasto.data < fim
        ),
    ).subquery()
    consulta = (
        select(
            Pet.id.label("pet_id"),
            Pet.nome,
            func.sum(lancamentos.c.arrecadado).label("arrecadado"),
            func.sum(lancamentos.c.gasto).label("gasto"),
        )
        .join(lancamentos, lancamentos.c.pet_id == Pet.id)
        .group_by(Pet.id, Pet.nome)
        .order_by(Pet.nome, Pet.id)
    )
    return list((await sessao.execute(consulta)).all())
