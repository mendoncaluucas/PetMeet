"""Regras de negocio do processo de adocao (RF14-18, RN01-RN04, RNF18).

Este e o modulo mais sensivel do sistema: aqui vive a regra critica do
enunciado (RN01/RF16) e a garantia de consistencia sob concorrencia (RNF18).
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import ConflitoError, RecursoNaoEncontradoError, RegraNegocioError
from app.esquemas.processo_adocao import ProcessoAdocaoAtualizarStatus, ProcessoAdocaoCriar
from app.modelos.enums import SituacaoAdocaoPet, StatusProcessoAdocao, StatusSaudePet
from app.modelos.pet import Pet
from app.modelos.processo_adocao import ProcessoAdocao
from app.repositorios import adotante as repo_adotante
from app.repositorios import pet as repo_pet
from app.repositorios import processo_adocao as repo_processo

_STATUS_ENCERRADOS = {StatusProcessoAdocao.FINALIZADO, StatusProcessoAdocao.CANCELADO}


async def criar_processo_adocao(
    sessao: AsyncSession, dados: ProcessoAdocaoCriar, responsavel_id: int
) -> ProcessoAdocao:
    # Trava a linha do pet ja na criacao: evita que dois adotantes iniciem processo
    # para o mesmo pet ao mesmo tempo (RNF18).
    pet = await repo_pet.obter_por_id_com_lock(sessao, dados.pet_id)
    if pet is None:
        raise RecursoNaoEncontradoError(f"Pet {dados.pet_id} nao encontrado.")

    if await repo_adotante.obter_por_id(sessao, dados.adotante_id) is None:
        raise RecursoNaoEncontradoError(f"Adotante {dados.adotante_id} nao encontrado.")

    # RN04: pet ja adotado nunca reabre processo.
    if pet.situacao_adocao == SituacaoAdocaoPet.ADOTADO:
        raise RegraNegocioError("Este pet ja foi adotado e nao pode iniciar um novo processo.")

    # RF17 (parte 1): nao permite dois processos concorrentes para o mesmo pet.
    if pet.situacao_adocao == SituacaoAdocaoPet.EM_PROCESSO_ADOCAO:
        raise RegraNegocioError("Este pet ja possui um processo de adocao em andamento.")

    processo = ProcessoAdocao(
        pet_id=dados.pet_id,
        adotante_id=dados.adotante_id,
        responsavel_id=responsavel_id,
        status=StatusProcessoAdocao.EM_ANALISE,
    )
    await repo_processo.criar(sessao, processo)

    # RN03: pet em processo deve ser identificado como 'em_processo_adocao'.
    pet.situacao_adocao = SituacaoAdocaoPet.EM_PROCESSO_ADOCAO

    await sessao.commit()
    await sessao.refresh(processo)
    return processo


async def obter_processo_ou_falhar(sessao: AsyncSession, processo_id: int) -> ProcessoAdocao:
    processo = await repo_processo.obter_por_id(sessao, processo_id)
    if processo is None:
        raise RecursoNaoEncontradoError(f"Processo de adocao {processo_id} nao encontrado.")
    return processo


async def listar_processos(
    sessao: AsyncSession,
    pagina: int,
    tamanho_pagina: int,
    pet_id: int | None = None,
    adotante_id: int | None = None,
) -> tuple[list[ProcessoAdocao], int]:
    return await repo_processo.listar(sessao, pagina, tamanho_pagina, pet_id, adotante_id)


async def atualizar_status_processo(
    sessao: AsyncSession, processo_id: int, dados: ProcessoAdocaoAtualizarStatus
) -> ProcessoAdocao:
    processo, pet = await _travar_para_transicao(sessao, processo_id)

    if dados.status == StatusProcessoAdocao.FINALIZADO:
        _finalizar(processo, pet, dados)
    else:
        processo.status = dados.status
        if dados.status == StatusProcessoAdocao.CANCELADO:
            pet.situacao_adocao = SituacaoAdocaoPet.DISPONIVEL

    await _commitar_transicao(sessao)
    await sessao.refresh(processo)
    return processo


async def _travar_para_transicao(
    sessao: AsyncSession, processo_id: int
) -> tuple[ProcessoAdocao, Pet]:
    """Trava pet e processo, nessa ordem, e so entao confere se o processo ainda pode mudar.

    A ordem pet -> processo e a mesma da criacao de processo, o que evita deadlock.
    """
    processo = await obter_processo_ou_falhar(sessao, processo_id)

    # Trava a linha do pet durante toda a transicao de status (RNF18): garante que,
    # se dois processos diferentes do MESMO pet tentarem finalizar ao mesmo tempo, o
    # segundo so prossegue depois que o primeiro commita -- e nesse ponto ele ja ve
    # a situacao_adocao atualizada e e rejeitado pela checagem de _finalizar.
    pet = await repo_pet.obter_por_id_com_lock(sessao, processo.pet_id)
    if pet is None:
        raise RecursoNaoEncontradoError(f"Pet {processo.pet_id} nao encontrado.")

    # O processo foi lido antes da trava: uma requisicao concorrente pode ter cancelado
    # ou finalizado ele nesse meio tempo. O refresh rele do banco e trava a linha --
    # um SELECT ... FOR UPDATE comum devolveria o objeto ja carregado na sessao, com o
    # status antigo, e as duas requisicoes passariam (DEF-06).
    await sessao.refresh(processo, with_for_update=True)
    if processo.status in _STATUS_ENCERRADOS:
        raise RegraNegocioError(
            f"Processo {processo_id} ja esta '{processo.status.value}' e nao pode ser alterado."
        )
    return processo, pet


def _finalizar(processo: ProcessoAdocao, pet: Pet, dados: ProcessoAdocaoAtualizarStatus) -> None:
    # RF17 (parte 2): outro processo do mesmo pet ja foi finalizado enquanto este
    # estava em analise/aprovado -- rejeita antes mesmo de tentar commitar.
    if pet.situacao_adocao == SituacaoAdocaoPet.ADOTADO:
        raise ConflitoError("Este pet ja foi adotado por meio de outro processo.")

    # RN01/RF16: pet em tratamento medico so finaliza com doenca identificada
    # e acompanhamento medico em dia confirmado pelo adotante.
    if pet.status_saude == StatusSaudePet.EM_TRATAMENTO_MEDICO:
        if not pet.doenca_atual:
            raise RegraNegocioError(
                "Pet esta em tratamento medico mas nao ha doenca identificada no cadastro; "
                "atualize o cadastro do pet antes de finalizar a adocao."
            )
        if not dados.acompanhamento_medico_em_dia:
            raise RegraNegocioError(
                "Pet em tratamento medico: a finalizacao exige que o adotante esteja de "
                "acordo com o acompanhamento medico (consultas semanais/mensais) em dia."
            )
        processo.acompanhamento_medico_em_dia = True

    processo.status = StatusProcessoAdocao.FINALIZADO
    pet.situacao_adocao = SituacaoAdocaoPet.ADOTADO


async def _commitar_transicao(sessao: AsyncSession) -> None:
    try:
        await sessao.commit()
    except IntegrityError as erro:
        # RN02: rede de seguranca do indice unico parcial (dois commits concorrentes
        # passaram pela checagem em memoria antes de qualquer um comitar).
        await sessao.rollback()
        raise ConflitoError(
            "Este pet ja possui um processo de adocao finalizado (conflito de concorrencia)."
        ) from erro
