"""Rotas de Doacao (RF12, RF13)."""

from fastapi import APIRouter, Depends, status

from app.dependencias import SessaoAsync, requer_perfil
from app.esquemas.comuns import PaginaResposta
from app.esquemas.doacao import DoacaoCriar, DoacaoResposta
from app.modelos.enums import PerfilUsuario
from app.rotas.parametros import IdNaConsulta, Pagina, TamanhoPagina
from app.servicos import doacao as servico_doacao

roteador = APIRouter(prefix="/doacoes", tags=["Doacoes"])

_requer_equipe = Depends(requer_perfil(PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO))


@roteador.post(
    "",
    response_model=DoacaoResposta,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_requer_equipe],
)
async def criar_doacao(sessao: SessaoAsync, dados: DoacaoCriar) -> DoacaoResposta:
    doacao = await servico_doacao.criar_doacao(sessao, dados)
    return DoacaoResposta.model_validate(doacao)


@roteador.get("", response_model=PaginaResposta[DoacaoResposta], dependencies=[_requer_equipe])
async def listar_doacoes(
    sessao: SessaoAsync,
    pagina: Pagina = 1,
    tamanho_pagina: TamanhoPagina = 20,
    padrinho_id: IdNaConsulta = None,
) -> PaginaResposta[DoacaoResposta]:
    itens, total = await servico_doacao.listar_doacoes(sessao, pagina, tamanho_pagina, padrinho_id)
    return PaginaResposta(
        itens=[DoacaoResposta.model_validate(item) for item in itens],
        total=total,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
    )
