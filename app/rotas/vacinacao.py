"""Rotas do catalogo de vacinas e do cartao de vacinacao (fase 2, H4 e H5)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.tempo import hoje_na_ong
from app.dependencias import SessaoAsync, requer_perfil
from app.esquemas.vacina import (
    AplicacaoAnular,
    AplicacaoCriar,
    AplicacaoResposta,
    CartaoVacinacao,
    VacinaAtualizar,
    VacinaCriar,
    VacinaResposta,
)
from app.modelos.enums import PerfilUsuario
from app.modelos.usuario import Usuario
from app.servicos import vacinacao as servico_vacinacao

roteador = APIRouter(tags=["Vacinacao"])

# Todos consultam; o catalogo e mantido por admin e veterinario (D9); aplicar e anular e
# so do veterinario (D7).
_requer_equipe_ou_veterinario = Depends(
    requer_perfil(PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO, PerfilUsuario.VETERINARIO)
)
_requer_admin_ou_veterinario = Depends(
    requer_perfil(PerfilUsuario.ADMIN, PerfilUsuario.VETERINARIO)
)
_Veterinario = Annotated[Usuario, Depends(requer_perfil(PerfilUsuario.VETERINARIO))]


# ------------------------------------------------------------------ catalogo


@roteador.get(
    "/vacinas", response_model=list[VacinaResposta], dependencies=[_requer_equipe_ou_veterinario]
)
async def listar_vacinas(
    sessao: SessaoAsync, incluir_inativas: Annotated[bool, Query()] = False
) -> list[VacinaResposta]:
    vacinas = await servico_vacinacao.listar_vacinas(sessao, incluir_inativas)
    return [VacinaResposta.model_validate(vacina) for vacina in vacinas]


@roteador.post(
    "/vacinas",
    response_model=VacinaResposta,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_requer_admin_ou_veterinario],
)
async def criar_vacina(sessao: SessaoAsync, dados: VacinaCriar) -> VacinaResposta:
    vacina = await servico_vacinacao.criar_vacina(sessao, dados)
    return VacinaResposta.model_validate(vacina)


@roteador.patch(
    "/vacinas/{vacina_id}",
    response_model=VacinaResposta,
    dependencies=[_requer_admin_ou_veterinario],
)
async def atualizar_vacina(
    sessao: SessaoAsync, vacina_id: int, dados: VacinaAtualizar
) -> VacinaResposta:
    """Vacina nao se apaga: desativar (`ativa: false`) tira das aplicacoes novas (H4.4)."""
    vacina = await servico_vacinacao.atualizar_vacina(sessao, vacina_id, dados)
    return VacinaResposta.model_validate(vacina)


# ------------------------------------------------------------------- cartao


@roteador.get(
    "/pets/{pet_id}/cartao-vacinacao",
    response_model=CartaoVacinacao,
    dependencies=[_requer_equipe_ou_veterinario],
)
async def cartao_vacinacao(sessao: SessaoAsync, pet_id: int) -> CartaoVacinacao:
    """Situacao por vacina (pela ultima aplicacao valida) e o historico completo."""
    return await servico_vacinacao.montar_cartao(sessao, pet_id, hoje=hoje_na_ong())


@roteador.post(
    "/pets/{pet_id}/aplicacoes-vacina",
    response_model=AplicacaoResposta,
    status_code=status.HTTP_201_CREATED,
)
async def registrar_aplicacao(
    sessao: SessaoAsync, veterinario: _Veterinario, pet_id: int, dados: AplicacaoCriar
) -> AplicacaoResposta:
    aplicacao = await servico_vacinacao.registrar_aplicacao(
        sessao, pet_id, dados, veterinario, hoje=hoje_na_ong()
    )
    return AplicacaoResposta.model_validate(aplicacao)


@roteador.post("/aplicacoes-vacina/{aplicacao_id}/anulacao", response_model=AplicacaoResposta)
async def anular_aplicacao(
    sessao: SessaoAsync, veterinario: _Veterinario, aplicacao_id: int, dados: AplicacaoAnular
) -> AplicacaoResposta:
    """A aplicacao continua no historico, marcada como anulada, e deixa de valer no status."""
    aplicacao = await servico_vacinacao.anular_aplicacao(sessao, aplicacao_id, dados, veterinario)
    return AplicacaoResposta.model_validate(aplicacao)
