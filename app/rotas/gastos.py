"""Rotas de gastos (fase 3, H9)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.tempo import hoje_na_ong
from app.dependencias import SessaoAsync, requer_perfil
from app.esquemas.comuns import PaginaResposta
from app.esquemas.gasto import EstornoCriar, GastoCriar, GastoResposta
from app.modelos.enums import CategoriaGasto, PerfilUsuario
from app.modelos.usuario import Usuario
from app.rotas.parametros import IdNaConsulta, IdNoCaminho, Pagina, TamanhoPagina
from app.servicos import gasto as servico_gasto

roteador = APIRouter(prefix="/gastos", tags=["Gastos"])

# A equipe registra; so o admin estorna (D14). O veterinario nao ve a parte financeira.
_requer_equipe = Depends(requer_perfil(PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO))
_Equipe = Annotated[Usuario, Depends(requer_perfil(PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO))]
_Admin = Annotated[Usuario, Depends(requer_perfil(PerfilUsuario.ADMIN))]


@roteador.post("", response_model=GastoResposta, status_code=status.HTTP_201_CREATED)
async def registrar_gasto(
    sessao: SessaoAsync, usuario: _Equipe, dados: GastoCriar
) -> GastoResposta:
    gasto = await servico_gasto.registrar(sessao, dados, usuario, hoje=hoje_na_ong())
    return GastoResposta.model_validate(gasto)


@roteador.get("", response_model=PaginaResposta[GastoResposta], dependencies=[_requer_equipe])
async def listar_gastos(
    sessao: SessaoAsync,
    categoria: CategoriaGasto | None = None,
    pet_id: IdNaConsulta = None,
    pagina: Pagina = 1,
    tamanho_pagina: TamanhoPagina = 20,
) -> PaginaResposta[GastoResposta]:
    """Mais recentes primeiro; cada estorno logo abaixo do gasto que ele corrige."""
    itens, total = await servico_gasto.listar(sessao, pagina, tamanho_pagina, categoria, pet_id)
    return PaginaResposta(
        itens=[GastoResposta.model_validate(item) for item in itens],
        total=total,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
    )


@roteador.post(
    "/{gasto_id}/estorno", response_model=GastoResposta, status_code=status.HTTP_201_CREATED
)
async def estornar_gasto(
    sessao: SessaoAsync, admin: _Admin, gasto_id: IdNoCaminho, dados: EstornoCriar
) -> GastoResposta:
    """Lancamento negativo com a data de hoje, ligado ao original (D13). O mes do original
    nao muda: o estorno sai dos totais no mes em que foi feito."""
    estorno = await servico_gasto.estornar(sessao, gasto_id, dados, admin, hoje=hoje_na_ong())
    return GastoResposta.model_validate(estorno)
