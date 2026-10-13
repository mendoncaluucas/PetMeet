"""Regras de negocio de Pet (RF01-05, RF19)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import obter_configuracoes
from app.core.excecoes import NaoAutorizadoError, RecursoNaoEncontradoError, RegraNegocioError
from app.esquemas.pet import (
    EstadoSaudePet,
    PetAtualizar,
    PetAtualizarStatusSaude,
    PetCriar,
)
from app.modelos.enums import EspeciePet, PerfilUsuario, SituacaoAdocaoPet, StatusSaudePet
from app.modelos.pet import Pet
from app.modelos.usuario import Usuario
from app.repositorios import pet as repo_pet
from app.servicos import auditoria as servico_auditoria

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
    sessao: AsyncSession, pet_id: int, dados: PetAtualizarStatusSaude, usuario: Usuario
) -> Pet:
    # Mesma trava da finalizacao da adocao: a alta e a finalizacao nao se cruzam, e o
    # "antes" gravado na auditoria e o que esta no banco, nao o de uma leitura antiga.
    pet = await repo_pet.obter_por_id_com_lock(sessao, pet_id)
    if pet is None:
        raise RecursoNaoEncontradoError(f"Pet {pet_id} nao encontrado.")

    antes = EstadoSaudePet.model_validate(pet)
    depois = EstadoSaudePet(
        status_saude=dados.status_saude,
        doenca_atual=(
            dados.doenca_atual
            if dados.status_saude == StatusSaudePet.EM_TRATAMENTO_MEDICO
            else None
        ),
    )
    if depois == antes:
        return await repo_pet.salvar(sessao, pet)  # nada mudou: so libera a trava

    da_alta = (
        antes.status_saude == StatusSaudePet.EM_TRATAMENTO_MEDICO
        and depois.status_saude != StatusSaudePet.EM_TRATAMENTO_MEDICO
    )
    if da_alta and usuario.perfil != PerfilUsuario.VETERINARIO:
        raise NaoAutorizadoError("So o veterinario pode dar alta de um tratamento medico.")

    pet.status_saude = depois.status_saude
    pet.doenca_atual = depois.doenca_atual
    servico_auditoria.registrar(
        sessao,
        usuario_id=usuario.id,
        entidade="pet",
        entidade_id=pet.id,
        acao="status_saude",
        antes=antes,
        depois=depois,
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
