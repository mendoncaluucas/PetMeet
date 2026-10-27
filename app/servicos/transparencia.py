"""Portal publico de prestacao de contas (fase 3, H11; decisoes D4, D13 e D15).

"Automatizado": o portal sai do que a equipe ja registra no dia a dia (doacoes e gastos),
sem relatorio montado a mao. As somas sao do banco; aqui so se monta o acumulado.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import intervalo_do_mes, ultimos_meses
from app.esquemas.publico import GastoDaCategoria, MesDoPortal, PetDoPortal, PortalTransparencia
from app.repositorios import transparencia as repo_transparencia

QUANTIDADE_DE_MESES = 12


async def montar_portal(sessao: AsyncSession, hoje: date) -> PortalTransparencia:
    """`hoje` e o dia em Brasilia (hoje_na_ong): o mes dele e o que esta em andamento."""
    mes_atual, fim = intervalo_do_mes(hoje)
    meses = ultimos_meses(mes_atual, QUANTIDADE_DE_MESES)
    inicio = meses[0]

    acumulado = await repo_transparencia.saldo_antes_de(sessao, inicio)
    arrecadado = await repo_transparencia.arrecadado_por_mes(sessao, inicio, fim)
    categorias: dict[str, list[GastoDaCategoria]] = defaultdict(list)
    gasto: dict[str, Decimal] = defaultdict(Decimal)
    for linha in await repo_transparencia.gasto_por_mes_e_categoria(sessao, inicio, fim):
        categorias[linha.mes].append(GastoDaCategoria(categoria=linha.categoria, valor=linha.total))
        gasto[linha.mes] += linha.total

    do_mais_antigo: list[MesDoPortal] = []
    for primeiro_dia in meses:
        chave = primeiro_dia.strftime("%Y-%m")
        arrecadado_no_mes = arrecadado.get(chave, Decimal("0.00"))
        gasto_no_mes = gasto.get(chave, Decimal("0.00"))
        saldo = arrecadado_no_mes - gasto_no_mes
        acumulado += saldo
        do_mais_antigo.append(
            MesDoPortal(
                mes=chave,
                em_andamento=primeiro_dia == mes_atual,
                arrecadado=arrecadado_no_mes,
                gasto=gasto_no_mes,
                saldo=saldo,
                saldo_acumulado=acumulado,
                gastos_por_categoria=categorias.get(chave, []),
            )
        )

    return PortalTransparencia(
        mes_inicial=meses[0].strftime("%Y-%m"),
        mes_final=mes_atual.strftime("%Y-%m"),
        arrecadado_no_periodo=sum((mes.arrecadado for mes in do_mais_antigo), Decimal("0.00")),
        gasto_no_periodo=sum((mes.gasto for mes in do_mais_antigo), Decimal("0.00")),
        saldo_acumulado=acumulado,
        meses=list(reversed(do_mais_antigo)),
        pets=[
            PetDoPortal.model_validate(linha._mapping)
            for linha in await repo_transparencia.movimento_por_pet(sessao, inicio, fim)
        ],
    )
