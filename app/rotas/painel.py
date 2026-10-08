"""Rota do resumo do Painel (DEF-09, DEF-10)."""

from fastapi import APIRouter, Depends

from app.core.tempo import hoje_na_ong
from app.dependencias import SessaoAsync, requer_perfil
from app.esquemas.painel import ResumoPainel
from app.modelos.enums import PerfilUsuario
from app.servicos import painel as servico_painel

roteador = APIRouter(prefix="/painel", tags=["Painel"])

# Traz nome de adotante nos processos: mesma restricao da listagem de processos.
_requer_equipe = Depends(requer_perfil(PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO))


@roteador.get("/resumo", response_model=ResumoPainel, dependencies=[_requer_equipe])
async def resumo(sessao: SessaoAsync) -> ResumoPainel:
    """Contagens e total de doacoes do mes (no fuso de Brasilia), calculados no banco."""
    return await servico_painel.montar_resumo(sessao, hoje=hoje_na_ong())
