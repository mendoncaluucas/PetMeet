"""Datas no fuso da ONG.

O container roda em UTC e o navegador, no fuso de quem usa. "Hoje" e "este mes" sao
sempre os de Brasilia, calculados aqui: entre 21h e meia-noite o dia em UTC ja e o
seguinte, e o Painel chegava a mostrar o mes errado no ultimo dia (DEF-09).
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

FUSO_DA_ONG = ZoneInfo("America/Sao_Paulo")


def hoje_na_ong(agora: datetime | None = None) -> date:
    """Data de hoje em Brasilia. `agora` existe para os testes fixarem o relogio."""
    return (agora or datetime.now(UTC)).astimezone(FUSO_DA_ONG).date()


def intervalo_do_mes(dia: date) -> tuple[date, date]:
    """Primeiro dia do mes de `dia` e primeiro dia do mes seguinte (fim exclusivo)."""
    inicio = dia.replace(day=1)
    fim = date(inicio.year + inicio.month // 12, inicio.month % 12 + 1, 1)
    return inicio, fim
