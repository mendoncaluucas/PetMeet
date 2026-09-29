"""Regras de negocio de Pet (RF01-05, RF19)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import obter_configuracoes
from app.core.excecoes import RecursoNaoEncontradoError, RegraNegocioError
from app.esquemas.pet import (
    PetAtualizar,
    PetAtualizarStatusSaude,
    PetCriar,
)
from app.modelos.enums import EspeciePet, SituacaoAdocaoPet, StatusSaudePet
from app.modelos.pet import Pet
from app.repositorios import pet as repo_pet

configuracoes = obter_configuracoes()


async def criar_pet(sessao: AsyncSession, dados: PetCriar) -> Pet:
    pet = Pet(
        nome=dados.nome,
        especie=dados.especie,
        idade=dados.idade,
        data_resgate=dados.data_resgate,
        status_saude=dados.status_saude,
        doenca_atual=dados.doenca_atual,
    )
    return await repo_pet.criar(sessao, pet)


async def obter_pet_ou_falhar(sessao: AsyncSession, pet_id: int) -> Pet:
    pet = await repo_pet.obter_por_id(sessao, pet_id)
    if pet is None:
        raise RecursoNaoEncontradoError(f"Pet {pet_id} nao encontrado.")
    return pet


async def listar_pets(
    sessao: AsyncSession,
    pagina: int,
    tamanho_pagina: int,
    especie: EspeciePet | None = None,
    status_saude: StatusSaudePet | None = None,
    situacao_adocao: SituacaoAdocaoPet | None = None,
) -> tuple[list[Pet], int]:
    return await repo_pet.listar(
        sessao, pagina, tamanho_pagina, especie, status_saude, situacao_adocao
    )


async def atualizar_pet(sessao: AsyncSession, pet_id: int, dados: PetAtualizar) -> Pet:
    pet = await obter_pet_ou_falhar(sessao, pet_id)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(pet, campo, valor)
    return await repo_pet.salvar(sessao, pet)


async def atualizar_status_saude(
    sessao: AsyncSession, pet_id: int, dados: PetAtualizarStatusSaude
) -> Pet:
    pet = await obter_pet_ou_falhar(sessao, pet_id)
    pet.status_saude = dados.status_saude
    pet.doenca_atual = (
        dados.doenca_atual if dados.status_saude == StatusSaudePet.EM_TRATAMENTO_MEDICO else None
    )
    return await repo_pet.salvar(sessao, pet)


def validar_upload_foto(content_type: str, tamanho_bytes: int) -> None:
    if content_type not in configuracoes.FORMATOS_IMAGEM_PERMITIDOS:
        raise RegraNegocioError(
            f"Formato de imagem nao suportado: {content_type}. "
            f"Formatos aceitos: {', '.join(configuracoes.FORMATOS_IMAGEM_PERMITIDOS)}."
        )
    limite_bytes = configuracoes.TAMANHO_MAX_UPLOAD_MB * 1024 * 1024
    if tamanho_bytes > limite_bytes:
        raise RegraNegocioError(
            f"Arquivo excede o limite de {configuracoes.TAMANHO_MAX_UPLOAD_MB}MB."
        )


async def definir_foto(sessao: AsyncSession, pet_id: int, url_foto: str) -> Pet:
    pet = await obter_pet_ou_falhar(sessao, pet_id)
    pet.foto_url = url_foto
    return await repo_pet.salvar(sessao, pet)
