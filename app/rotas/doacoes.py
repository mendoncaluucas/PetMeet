"""Rotas de Doacao (RF12, RF13)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.tempo import hoje_na_ong
from app.dependencias import SessaoAsync, requer_perfil
from app.esquemas.comuns import PaginaResposta
from app.esquemas.doacao import DoacaoCriar, DoacaoResposta
from app.esquemas.gasto import EstornoCriar
from app.modelos.enums import PerfilUsuario
from app.modelos.usuario import Usuario
from app.rotas.parametros import IdNaConsulta, IdNoCaminho, Pagina, TamanhoPagina
from app.servicos import doacao as servico_doacao

roteador = APIRouter(prefix="/doacoes", tags=["Doacoes"])

_requer_equipe = Depends(requer_perfil(PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO))
_Equipe = Annotated[Usuario, Depends(requer_perfil(PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO))]
# Estorno mexe em dinheiro ja publicado: so o admin (D14).
_Admin = Annotated[Usuario, Depends(requer_perfil(PerfilUsuario.ADMIN))]


@roteador.post(
    "",
    response_model=DoacaoResposta,
    status_code=status.HTTP_201_CREATED,
)
async def criar_doacao(sessao: SessaoAsync, usuario: _Equipe, dados: DoacaoCriar) -> DoacaoResposta:
    doacao = await servico_doacao.criar_doacao(sessao, dados, usuario, hoje=hoje_na_ong())
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


@roteador.post(
    "/{doacao_id}/estorno",
    response_model=DoacaoResposta,
    status_code=status.HTTP_201_CREATED,
)
async def estornar_doacao(
    sessao: SessaoAsync, admin: _Admin, doacao_id: IdNoCaminho, dados: EstornoCriar
) -> DoacaoResposta:
    """Lancamento negativo com a data de hoje, ligado a doacao original (D13). A doacao
    original nao muda nem some: o mes dela continua como foi publicado."""
    estorno = await servico_doacao.estornar(sessao, doacao_id, dados, admin, hoje=hoje_na_ong())
    return DoacaoResposta.model_validate(estorno)
