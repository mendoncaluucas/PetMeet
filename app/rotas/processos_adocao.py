"""Rotas do processo de adocao (RF14-18)."""

from fastapi import APIRouter, Depends, status

from app.dependencias import SessaoAsync, UsuarioAtual, requer_perfil
from app.esquemas.comuns import PaginaResposta
from app.esquemas.processo_adocao import (
    ProcessoAdocaoAtualizarStatus,
    ProcessoAdocaoCriar,
    ProcessoAdocaoResposta,
)
from app.modelos.enums import PerfilUsuario
from app.rotas.parametros import IdNaConsulta, IdNoCaminho, Pagina, TamanhoPagina
from app.servicos import processo_adocao as servico_processo

roteador = APIRouter(prefix="/processos-adocao", tags=["Processos de Adocao"])

_requer_equipe = Depends(requer_perfil(PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO))


@roteador.post(
    "",
    response_model=ProcessoAdocaoResposta,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_requer_equipe],
)
async def criar_processo(
    sessao: SessaoAsync, usuario: UsuarioAtual, dados: ProcessoAdocaoCriar
) -> ProcessoAdocaoResposta:
    processo = await servico_processo.criar_processo_adocao(sessao, dados, usuario.id)
    return ProcessoAdocaoResposta.model_validate(processo)


@roteador.get(
    "", response_model=PaginaResposta[ProcessoAdocaoResposta], dependencies=[_requer_equipe]
)
async def listar_processos(
    sessao: SessaoAsync,
    pagina: Pagina = 1,
    tamanho_pagina: TamanhoPagina = 20,
    pet_id: IdNaConsulta = None,
    adotante_id: IdNaConsulta = None,
) -> PaginaResposta[ProcessoAdocaoResposta]:
    itens, total = await servico_processo.listar_processos(
        sessao, pagina, tamanho_pagina, pet_id, adotante_id
    )
    return PaginaResposta(
        itens=[ProcessoAdocaoResposta.model_validate(item) for item in itens],
        total=total,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
    )


@roteador.get(
    "/{processo_id}", response_model=ProcessoAdocaoResposta, dependencies=[_requer_equipe]
)
async def obter_processo(sessao: SessaoAsync, processo_id: IdNoCaminho) -> ProcessoAdocaoResposta:
    processo = await servico_processo.obter_processo_ou_falhar(sessao, processo_id)
    return ProcessoAdocaoResposta.model_validate(processo)


@roteador.patch(
    "/{processo_id}/status", response_model=ProcessoAdocaoResposta, dependencies=[_requer_equipe]
)
async def atualizar_status(
    sessao: SessaoAsync, processo_id: IdNoCaminho, dados: ProcessoAdocaoAtualizarStatus
) -> ProcessoAdocaoResposta:
    processo = await servico_processo.atualizar_status_processo(sessao, processo_id, dados)
    return ProcessoAdocaoResposta.model_validate(processo)
