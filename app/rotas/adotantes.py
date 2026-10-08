"""Rotas de Adotante (RF06-08). Dado pessoal sensivel: exige autenticacao (RN07/LGPD)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.dependencias import SessaoAsync, requer_perfil
from app.esquemas.adotante import AdotanteAtualizar, AdotanteCriar, AdotanteResposta
from app.esquemas.comuns import PaginaResposta
from app.modelos.enums import PerfilUsuario
from app.servicos import adotante as servico_adotante

roteador = APIRouter(prefix="/adotantes", tags=["Adotantes"])

_requer_equipe = Depends(requer_perfil(PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO))


@roteador.post(
    "",
    response_model=AdotanteResposta,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_requer_equipe],
)
async def criar_adotante(sessao: SessaoAsync, dados: AdotanteCriar) -> AdotanteResposta:
    adotante = await servico_adotante.criar_adotante(sessao, dados)
    return AdotanteResposta.model_validate(adotante)


@roteador.get("", response_model=PaginaResposta[AdotanteResposta], dependencies=[_requer_equipe])
async def listar_adotantes(
    sessao: SessaoAsync,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamanho_pagina: Annotated[int, Query(ge=1, le=100)] = 20,
    incluir_inativos: bool = False,
) -> PaginaResposta[AdotanteResposta]:
    itens, total = await servico_adotante.listar_adotantes(
        sessao, pagina, tamanho_pagina, incluir_inativos
    )
    return PaginaResposta(
        itens=[AdotanteResposta.model_validate(item) for item in itens],
        total=total,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
    )


@roteador.get("/{adotante_id}", response_model=AdotanteResposta, dependencies=[_requer_equipe])
async def obter_adotante(sessao: SessaoAsync, adotante_id: int) -> AdotanteResposta:
    adotante = await servico_adotante.obter_adotante_ou_falhar(sessao, adotante_id)
    return AdotanteResposta.model_validate(adotante)


@roteador.patch("/{adotante_id}", response_model=AdotanteResposta, dependencies=[_requer_equipe])
async def atualizar_adotante(
    sessao: SessaoAsync, adotante_id: int, dados: AdotanteAtualizar
) -> AdotanteResposta:
    adotante = await servico_adotante.atualizar_adotante(sessao, adotante_id, dados)
    return AdotanteResposta.model_validate(adotante)


@roteador.delete(
    "/{adotante_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_requer_equipe]
)
async def excluir_adotante(sessao: SessaoAsync, adotante_id: int) -> None:
    """Exclui adotante sem processo de adocao. Com processo, responde 409: inative."""
    await servico_adotante.excluir_adotante(sessao, adotante_id)
