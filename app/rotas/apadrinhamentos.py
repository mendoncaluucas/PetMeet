"""Rotas do apadrinhamento (fase 3, H7)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.tempo import hoje_na_ong
from app.dependencias import SessaoAsync, requer_perfil
from app.esquemas.apadrinhamento import (
    ApadrinhamentoCriar,
    ApadrinhamentoEncerrar,
    ApadrinhamentoResposta,
    EsperadoRecebido,
    PadrinhosDoPet,
)
from app.esquemas.comuns import PaginaResposta
from app.modelos.enums import PerfilUsuario
from app.rotas.parametros import IdNaConsulta, IdNoCaminho, Pagina, TamanhoPagina
from app.servicos import apadrinhamento as servico_apadrinhamento
from app.servicos import esperado_recebido as servico_esperado_recebido

roteador = APIRouter(tags=["Apadrinhamentos"])

# Parte financeira: so a equipe (D14). O veterinario ve apenas a contagem na ficha do pet.
_requer_equipe = Depends(requer_perfil(PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO))
_requer_equipe_ou_veterinario = Depends(
    requer_perfil(PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO, PerfilUsuario.VETERINARIO)
)


@roteador.get(
    "/apadrinhamentos",
    response_model=PaginaResposta[ApadrinhamentoResposta],
    dependencies=[_requer_equipe],
)
async def listar_apadrinhamentos(
    sessao: SessaoAsync,
    padrinho_id: IdNaConsulta = None,
    pet_id: IdNaConsulta = None,
    incluir_encerrados: Annotated[bool, Query()] = False,
    pagina: Pagina = 1,
    tamanho_pagina: TamanhoPagina = 20,
) -> PaginaResposta[ApadrinhamentoResposta]:
    itens, total = await servico_apadrinhamento.listar(
        sessao, pagina, tamanho_pagina, padrinho_id, pet_id, incluir_encerrados
    )
    return PaginaResposta(
        itens=[ApadrinhamentoResposta.model_validate(item) for item in itens],
        total=total,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
    )


@roteador.get(
    "/apadrinhamentos/esperado-recebido",
    response_model=PaginaResposta[EsperadoRecebido],
    dependencies=[_requer_equipe],
)
async def esperado_recebido(
    sessao: SessaoAsync,
    so_pendentes: Annotated[bool, Query()] = False,
    pagina: Pagina = 1,
    tamanho_pagina: TamanhoPagina = 20,
) -> PaginaResposta[EsperadoRecebido]:
    """Mes a mes, quanto cada padrinho combinou e quanto doou, nos ultimos 12 meses (H10).

    Mes fechado parcial ou sem doacao conta como pendente; o mes corrente nao e atraso.
    Quem tem pendencia vem primeiro.
    """
    itens, total = await servico_esperado_recebido.listar(
        sessao, hoje_na_ong(), pagina, tamanho_pagina, so_pendentes
    )
    return PaginaResposta(itens=itens, total=total, pagina=pagina, tamanho_pagina=tamanho_pagina)


@roteador.post(
    "/apadrinhamentos",
    response_model=ApadrinhamentoResposta,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_requer_equipe],
)
async def criar_apadrinhamento(
    sessao: SessaoAsync, dados: ApadrinhamentoCriar
) -> ApadrinhamentoResposta:
    """Um ativo por padrinho e pet (409); pet adotado nao recebe (422)."""
    apadrinhamento = await servico_apadrinhamento.criar(sessao, dados, hoje=hoje_na_ong())
    return ApadrinhamentoResposta.model_validate(apadrinhamento)


@roteador.post(
    "/apadrinhamentos/{apadrinhamento_id}/encerramento",
    response_model=ApadrinhamentoResposta,
    dependencies=[_requer_equipe],
)
async def encerrar_apadrinhamento(
    sessao: SessaoAsync, apadrinhamento_id: IdNoCaminho, dados: ApadrinhamentoEncerrar
) -> ApadrinhamentoResposta:
    """O valor combinado nao se edita: para mudar, encerra-se e abre-se outro (H7.7)."""
    apadrinhamento = await servico_apadrinhamento.encerrar(
        sessao, apadrinhamento_id, dados, hoje=hoje_na_ong()
    )
    return ApadrinhamentoResposta.model_validate(apadrinhamento)


@roteador.get(
    "/pets/{pet_id}/padrinhos",
    response_model=PadrinhosDoPet,
    dependencies=[_requer_equipe_ou_veterinario],
)
async def padrinhos_do_pet(sessao: SessaoAsync, pet_id: IdNoCaminho) -> PadrinhosDoPet:
    """So a contagem de padrinhos ativos, sem nomes: serve a qualquer perfil."""
    ativos = await servico_apadrinhamento.contar_ativos_do_pet(sessao, pet_id)
    return PadrinhosDoPet(pet_id=pet_id, ativos=ativos)
