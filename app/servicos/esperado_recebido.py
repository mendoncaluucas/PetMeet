"""Esperado x recebido dos padrinhos (fase 3, H10): para a equipe cobrar quem atrasou."""

from collections import defaultdict
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import intervalo_do_mes, ultimos_meses
from app.esquemas.apadrinhamento import EsperadoRecebido, MesDoPadrinho, SituacaoDoMes
from app.repositorios import esperado_recebido as repo_esperado_recebido

QUANTIDADE_DE_MESES = 12


async def listar(
    sessao: AsyncSession, hoje: date, pagina: int, tamanho_pagina: int, so_pendentes: bool
) -> tuple[list[EsperadoRecebido], int]:
    """`hoje` e o dia em Brasilia (hoje_na_ong): o mes dele e o que esta em andamento."""
    mes_atual = hoje.replace(day=1)
    meses = [intervalo_do_mes(mes) for mes in ultimos_meses(mes_atual, QUANTIDADE_DE_MESES)]
    grade = repo_esperado_recebido.montar_grade(meses, mes_atual)

    padrinhos, total = await repo_esperado_recebido.listar_padrinhos(
        sessao, grade, pagina, tamanho_pagina, so_pendentes
    )
    ids = [padrinho.padrinho_id for padrinho in padrinhos]
    por_padrinho: dict[int, list[MesDoPadrinho]] = defaultdict(list)
    for linha in await repo_esperado_recebido.meses_dos_padrinhos(sessao, grade, ids):
        por_padrinho[linha.padrinho_id].append(
            MesDoPadrinho(
                mes=linha.inicio.strftime("%Y-%m"),
                esperado=linha.esperado,
                recebido=linha.recebido,
                diferenca=linha.recebido - linha.esperado,
                situacao=SituacaoDoMes(linha.situacao),
            )
        )

    itens = [
        EsperadoRecebido(
            padrinho_id=padrinho.padrinho_id,
            padrinho_nome=padrinho.padrinho_nome,
            meses_pendentes=padrinho.pendentes,
            meses=por_padrinho[padrinho.padrinho_id],
        )
        for padrinho in padrinhos
    ]
    return itens, total
