"""Rotas de Pet (RF01-05, RF19)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.armazenamento import obter_armazenamento
from app.dependencias import SessaoAsync, UsuarioAtual, requer_perfil
from app.esquemas.comuns import PaginaResposta
from app.esquemas.pet import (
    PetAtualizar,
    PetAtualizarStatusSaude,
    PetCriar,
    PetResposta,
)
from app.modelos.enums import EspeciePet, PerfilUsuario, SituacaoAdocaoPet, StatusSaudePet
from app.servicos import pet as servico_pet

roteador = APIRouter(prefix="/pets", tags=["Pets"])

_requer_equipe = Depends(requer_perfil(PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO))


@roteador.post(
    "",
    response_model=PetResposta,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_requer_equipe],
)
async def criar_pet(sessao: SessaoAsync, dados: PetCriar) -> PetResposta:
    pet = await servico_pet.criar_pet(sessao, dados)
    return PetResposta.model_validate(pet)


@roteador.get("", response_model=PaginaResposta[PetResposta])
async def listar_pets(
    sessao: SessaoAsync,
    _usuario: UsuarioAtual,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamanho_pagina: Annotated[int, Query(ge=1, le=100)] = 20,
    especie: EspeciePet | None = None,
    status_saude: StatusSaudePet | None = None,
    situacao_adocao: SituacaoAdocaoPet | None = None,
) -> PaginaResposta[PetResposta]:
    itens, total = await servico_pet.listar_pets(
        sessao, pagina, tamanho_pagina, especie, status_saude, situacao_adocao
    )
    return PaginaResposta(
        itens=[PetResposta.model_validate(item) for item in itens],
        total=total,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
    )


@roteador.get("/{pet_id}", response_model=PetResposta)
async def obter_pet(sessao: SessaoAsync, _usuario: UsuarioAtual, pet_id: int) -> PetResposta:
    pet = await servico_pet.obter_pet_ou_falhar(sessao, pet_id)
    return PetResposta.model_validate(pet)


@roteador.patch("/{pet_id}", response_model=PetResposta, dependencies=[_requer_equipe])
async def atualizar_pet(sessao: SessaoAsync, pet_id: int, dados: PetAtualizar) -> PetResposta:
    pet = await servico_pet.atualizar_pet(sessao, pet_id, dados)
    return PetResposta.model_validate(pet)


@roteador.patch("/{pet_id}/status-saude", response_model=PetResposta, dependencies=[_requer_equipe])
async def atualizar_status_saude(
    sessao: SessaoAsync, pet_id: int, dados: PetAtualizarStatusSaude
) -> PetResposta:
    pet = await servico_pet.atualizar_status_saude(sessao, pet_id, dados)
    return PetResposta.model_validate(pet)


# A situacao de adocao nao tem rota propria: ela muda so pelo processo de adocao
# (abrir, cancelar, finalizar). A rota manual que existia permitia marcar como adotado
# um pet em tratamento medico, sem processo nenhum (DEF-03).


@roteador.post("/{pet_id}/foto", response_model=PetResposta, dependencies=[_requer_equipe])
async def enviar_foto(
    sessao: SessaoAsync, pet_id: int, arquivo: Annotated[UploadFile, File()]
) -> PetResposta:
    conteudo = await arquivo.read()
    servico_pet.validar_upload_foto(arquivo.content_type or "", len(conteudo))

    armazenamento = obter_armazenamento()
    url_foto = await armazenamento.salvar(arquivo.filename or "foto.jpg", conteudo)

    pet = await servico_pet.definir_foto(sessao, pet_id, url_foto)
    return PetResposta.model_validate(pet)
