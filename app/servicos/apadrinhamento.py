"""Regras do apadrinhamento (fase 3, H7; decisoes D11 e D12)."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import ConflitoError, RecursoNaoEncontradoError, RegraNegocioError
from app.esquemas.apadrinhamento import ApadrinhamentoCriar, ApadrinhamentoEncerrar
from app.modelos.apadrinhamento import Apadrinhamento
from app.modelos.enums import SituacaoAdocaoPet
from app.repositorios import apadrinhamento as repo_apadrinhamento
from app.repositorios import padrinho as repo_padrinho
from app.repositorios import pet as repo_pet
from app.servicos.unicidade import gravar_sem_duplicar

_JA_ATIVO = "Este padrinho ja apadrinha este pet. Encerre o atual antes de abrir outro."


async def criar(sessao: AsyncSession, dados: ApadrinhamentoCriar, hoje: date) -> Apadrinhamento:
    """`hoje` e o dia em Brasilia (hoje_na_ong)."""
    if dados.data_inicio > hoje:
        raise RegraNegocioError("A data de inicio nao pode estar no futuro.")
    if await repo_padrinho.obter_por_id(sessao, dados.padrinho_id) is None:
        raise RecursoNaoEncontradoError(f"Padrinho {dados.padrinho_id} nao encontrado.")

    # Mesma trava da finalizacao da adocao: uma finalizacao simultanea espera este
    # apadrinhamento (e o encerra), ou este ve o pet ja adotado. Sem a trava, o pet seria
    # adotado sem ver o apadrinhamento novo, que ficaria ativo para sempre (D12).
    pet = await repo_pet.obter_por_id_com_lock(sessao, dados.pet_id)
    if pet is None:
        raise RecursoNaoEncontradoError(f"Pet {dados.pet_id} nao encontrado.")
    if pet.situacao_adocao == SituacaoAdocaoPet.ADOTADO:
        raise RegraNegocioError("Pet adotado nao recebe apadrinhamento novo.")
    if await repo_apadrinhamento.existe_ativo(sessao, dados.padrinho_id, dados.pet_id):
        raise ConflitoError(_JA_ATIVO)

    apadrinhamento = Apadrinhamento(
        padrinho_id=dados.padrinho_id,
        pet_id=dados.pet_id,
        valor_mensal=dados.valor_mensal,
        data_inicio=dados.data_inicio,
    )
    sessao.add(apadrinhamento)
    # Dois cadastros iguais ao mesmo tempo: o indice parcial barra o segundo, com o mesmo 409.
    await gravar_sem_duplicar(sessao, sessao.commit(), _JA_ATIVO, erro=ConflitoError)
    return await _com_nomes(sessao, apadrinhamento.id)


async def encerrar(
    sessao: AsyncSession, apadrinhamento_id: int, dados: ApadrinhamentoEncerrar, hoje: date
) -> Apadrinhamento:
    apadrinhamento = await repo_apadrinhamento.obter_com_lock(sessao, apadrinhamento_id)
    if apadrinhamento is None:
        raise RecursoNaoEncontradoError(f"Apadrinhamento {apadrinhamento_id} nao encontrado.")
    if apadrinhamento.data_fim is not None:
        raise RegraNegocioError("Este apadrinhamento ja foi encerrado.")
    if dados.data_fim > hoje:
        raise RegraNegocioError("A data de fim nao pode estar no futuro.")
    if dados.data_fim < apadrinhamento.data_inicio:
        raise RegraNegocioError("A data de fim nao pode ser anterior a de inicio.")

    apadrinhamento.data_fim = dados.data_fim
    await sessao.commit()
    return await _com_nomes(sessao, apadrinhamento.id)


async def listar(
    sessao: AsyncSession,
    pagina: int,
    tamanho_pagina: int,
    padrinho_id: int | None,
    pet_id: int | None,
    incluir_encerrados: bool,
) -> tuple[list[Apadrinhamento], int]:
    return await repo_apadrinhamento.listar(
        sessao, pagina, tamanho_pagina, padrinho_id, pet_id, incluir_encerrados
    )


async def contar_ativos_do_pet(sessao: AsyncSession, pet_id: int) -> int:
    if await repo_pet.obter_por_id(sessao, pet_id) is None:
        raise RecursoNaoEncontradoError(f"Pet {pet_id} nao encontrado.")
    return await repo_apadrinhamento.contar_ativos_do_pet(sessao, pet_id)


async def _com_nomes(sessao: AsyncSession, apadrinhamento_id: int) -> Apadrinhamento:
    apadrinhamento = await repo_apadrinhamento.obter(sessao, apadrinhamento_id)
    assert apadrinhamento is not None  # acabou de ser gravado nesta sessao
    return apadrinhamento
