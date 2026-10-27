"""Portal publico de prestacao de contas (fase 3, H11)."""

from fastapi import APIRouter

from app.core.tempo import hoje_na_ong
from app.dependencias import SessaoAsync
from app.esquemas.publico import PortalTransparencia
from app.servicos import transparencia as servico_transparencia

roteador = APIRouter(tags=["Transparencia"])


# Sem requer_perfil, de proposito: qualquer visitante ve, sem login (D4). Por isso a
# resposta usa os schemas de app/esquemas/publico.py, que so tem totais.
@roteador.get("/transparencia", response_model=PortalTransparencia)
async def portal(sessao: SessaoAsync) -> PortalTransparencia:
    """Arrecadado, gasto e saldo dos ultimos 12 meses, gastos por categoria e por pet."""
    return await servico_transparencia.montar_portal(sessao, hoje=hoje_na_ong())
