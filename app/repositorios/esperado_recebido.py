"""Esperado x recebido dos padrinhos (fase 3, H10): a grade padrinho x mes, somada no banco.

Esperado: soma dos valores mensais dos apadrinhamentos ativos em algum dia do mes (H10.2).
Recebido: soma das doacoes do padrinho com data no mes, ja com os estornos, que sao
lancamentos negativos no mes em que foram feitos (D13).
"""

from datetime import date

from sqlalchemy import (
    CTE,
    BindParameter,
    Date,
    Numeric,
    Row,
    String,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    or_,
    select,
    true,
    values,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.esquemas.apadrinhamento import SituacaoDoMes
from app.modelos.apadrinhamento import Apadrinhamento
from app.modelos.doacao import Doacao
from app.modelos.padrinho import Padrinho

PENDENTES = (SituacaoDoMes.PARCIAL.value, SituacaoDoMes.SEM_DOACAO.value)
# Zero com duas casas: com o 0 inteiro, mes sem lancamento saia "0" no JSON, e nao "0.00".
_ZERO = cast(literal(0), Numeric(10, 2))


def montar_grade(meses: list[tuple[date, date]], mes_atual: date) -> CTE:
    """Uma linha por padrinho e mes: (padrinho_id, padrinho_nome, inicio, esperado,
    recebido, situacao), com `meses` em pares (primeiro dia, primeiro dia do seguinte).

    Entram os padrinhos com apadrinhamento ativo em algum dia do periodo: quem so doou,
    sem compromisso, nao tem o que cobrar.

    Cada soma e uma passada so, agrupada por padrinho e mes. Com uma subconsulta por
    celula da grade, 2 mil padrinhos levavam de 1 a 4 segundos por pagina.
    """
    tabela_meses = select(
        values(column("inicio", Date), column("fim", Date), name="valores").data(meses)
    ).cte("meses")
    esperado = (
        select(
            Apadrinhamento.padrinho_id,
            tabela_meses.c.inicio,
            func.sum(Apadrinhamento.valor_mensal).label("total"),
        )
        .join(
            tabela_meses,
            and_(
                Apadrinhamento.data_inicio < tabela_meses.c.fim,
                or_(
                    Apadrinhamento.data_fim.is_(None),
                    Apadrinhamento.data_fim >= tabela_meses.c.inicio,
                ),
            ),
        )
        .group_by(Apadrinhamento.padrinho_id, tabela_meses.c.inicio)
        .cte("esperado")
    )
    recebido = (
        select(Doacao.padrinho_id, tabela_meses.c.inicio, func.sum(Doacao.valor).label("total"))
        .join(
            tabela_meses,
            and_(Doacao.data >= tabela_meses.c.inicio, Doacao.data < tabela_meses.c.fim),
        )
        .where(Doacao.padrinho_id.is_not(None))
        .group_by(Doacao.padrinho_id, tabela_meses.c.inicio)
        .cte("recebido")
    )
    base = (
        select(
            Padrinho.id.label("padrinho_id"),
            Padrinho.nome.label("padrinho_nome"),
            tabela_meses.c.inicio,
            func.coalesce(esperado.c.total, _ZERO).label("esperado"),
            func.coalesce(recebido.c.total, _ZERO).label("recebido"),
        )
        .select_from(Padrinho)
        .join(tabela_meses, true())
        .outerjoin(
            esperado,
            and_(
                esperado.c.padrinho_id == Padrinho.id,
                esperado.c.inicio == tabela_meses.c.inicio,
            ),
        )
        .outerjoin(
            recebido,
            and_(
                recebido.c.padrinho_id == Padrinho.id,
                recebido.c.inicio == tabela_meses.c.inicio,
            ),
        )
        # Ter esperado em algum mes e o mesmo que estar ativo em algum dia do periodo.
        .where(Padrinho.id.in_(select(esperado.c.padrinho_id)))
        .cte("base")
    )
    situacao = case(
        (base.c.esperado == 0, _texto(SituacaoDoMes.SEM_COMPROMISSO)),
        (base.c.recebido >= base.c.esperado, _texto(SituacaoDoMes.EM_DIA)),
        # Mes corrente ainda nao pago nao e atraso (H10.3).
        (base.c.inicio == mes_atual, _texto(SituacaoDoMes.EM_ANDAMENTO)),
        (base.c.recebido > 0, _texto(SituacaoDoMes.PARCIAL)),
        # Recebido zero ou negativo (so o estorno de uma doacao de outro mes).
        else_=_texto(SituacaoDoMes.SEM_DOACAO),
    )
    return select(*base.c, situacao.label("situacao")).cte("grade")


def _texto(situacao: SituacaoDoMes) -> BindParameter[str]:
    return literal(situacao.value, String)


async def listar_padrinhos(
    sessao: AsyncSession, grade: CTE, pagina: int, tamanho_pagina: int, so_pendentes: bool
) -> tuple[list[Row], int]:
    """(padrinho_id, padrinho_nome, pendentes): quem tem pendencia primeiro, depois o nome."""
    resumo = (
        select(
            grade.c.padrinho_id,
            grade.c.padrinho_nome,
            func.count().filter(grade.c.situacao.in_(PENDENTES)).label("pendentes"),
        )
        .group_by(grade.c.padrinho_id, grade.c.padrinho_nome)
        .subquery()
    )
    filtros = [resumo.c.pendentes > 0] if so_pendentes else []
    total = (
        await sessao.execute(select(func.count()).select_from(resumo).where(*filtros))
    ).scalar_one()
    consulta = (
        select(resumo)
        .where(*filtros)
        .order_by((resumo.c.pendentes > 0).desc(), resumo.c.padrinho_nome, resumo.c.padrinho_id)
        .offset((pagina - 1) * tamanho_pagina)
        .limit(tamanho_pagina)
    )
    return list((await sessao.execute(consulta)).all()), total


async def meses_dos_padrinhos(sessao: AsyncSession, grade: CTE, ids: list[int]) -> list[Row]:
    """As linhas da grade dos padrinhos da pagina, do mes mais recente para o mais antigo."""
    consulta = (
        select(grade)
        .where(grade.c.padrinho_id.in_(ids))
        .order_by(grade.c.padrinho_id, grade.c.inicio.desc())
    )
    return list((await sessao.execute(consulta)).all())
