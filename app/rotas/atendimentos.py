"""Rotas da ficha clinica (fase 2, H3)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.tempo import hoje_na_ong
from app.dependencias import SessaoAsync, requer_perfil
from app.esquemas.atendimento_clinico import (
    AtendimentoAnular,
    AtendimentoCriar,
    AtendimentoResposta,
)
from app.esquemas.comuns import PaginaResposta
from app.modelos.enums import PerfilUsuario
from app.modelos.usuario import Usuario
from app.servicos import atendimento_clinico as servico_atendimento

roteador = APIRouter(tags=["Ficha clinica"])

# A equipe consulta a ficha; registrar e anular e so do veterinario (D7).
_requer_equipe_ou_veterinario = Depends(
    requer_perfil(PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO, PerfilUsuario.VETERINARIO)
)
_Veterinario = Annotated[Usuario, Depends(requer_perfil(PerfilUsuario.VETERINARIO))]


@roteador.get(
    "/pets/{pet_id}/atendimentos",
    response_model=PaginaResposta[AtendimentoResposta],
    dependencies=[_requer_equipe_ou_veterinario],
)
async def listar_atendimentos(
    sessao: SessaoAsync,
    pet_id: int,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamanho_pagina: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaResposta[AtendimentoResposta]:
    itens, total = await servico_atendimento.listar_do_pet(sessao, pet_id, pagina, tamanho_pagina)
    return PaginaResposta(
        itens=[AtendimentoResposta.model_validate(item) for item in itens],
        total=total,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
    )


@roteador.post(
    "/pets/{pet_id}/atendimentos",
    response_model=AtendimentoResposta,
    status_code=status.HTTP_201_CREATED,
)
async def registrar_atendimento(
    sessao: SessaoAsync, veterinario: _Veterinario, pet_id: int, dados: AtendimentoCriar
) -> AtendimentoResposta:
    atendimento = await servico_atendimento.registrar(
        sessao, pet_id, dados, veterinario, hoje=hoje_na_ong()
    )
    return AtendimentoResposta.model_validate(atendimento)


@roteador.post("/atendimentos/{atendimento_id}/anulacao", response_model=AtendimentoResposta)
async def anular_atendimento(
    sessao: SessaoAsync, veterinario: _Veterinario, atendimento_id: int, dados: AtendimentoAnular
) -> AtendimentoResposta:
    """O atendimento continua na ficha, marcado como anulado (D8)."""
    atendimento = await servico_atendimento.anular(sessao, atendimento_id, dados, veterinario)
    return AtendimentoResposta.model_validate(atendimento)
