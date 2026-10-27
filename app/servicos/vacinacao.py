"""Regras do catalogo de vacinas e do cartao de vacinacao (fase 2, H4 e H5)."""

from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excecoes import ConflitoError, RecursoNaoEncontradoError, RegraNegocioError
from app.esquemas.vacina import (
    AlertasVacina,
    AlertaVacina,
    AplicacaoAnular,
    AplicacaoCriar,
    AplicacaoResposta,
    CartaoVacinacao,
    SituacaoVacina,
    StatusVacina,
    VacinaAtualizar,
    VacinaCriar,
)
from app.modelos.usuario import Usuario
from app.modelos.vacina import AplicacaoVacina, Vacina
from app.repositorios import pet as repo_pet
from app.repositorios import vacina as repo_vacina
from app.servicos.unicidade import gravar_sem_duplicar

# "Vencendo" vai de hoje ate hoje + 30 dias (D3).
JANELA_VENCENDO_DIAS = 30

# Ordem do cartao: a mais urgente primeiro. Um status novo sem lugar aqui da KeyError.
_PRIORIDADE = {
    StatusVacina.VENCIDA: 0,
    StatusVacina.VENCENDO: 1,
    StatusVacina.EM_DIA: 2,
    StatusVacina.SEM_REFORCO: 3,
}

_NOME_EM_USO = "Ja existe uma vacina com este nome no catalogo."
_APLICACAO_REPETIDA = "Esta vacina ja foi registrada para este pet nesta data."


def status_da_dose(proxima_dose: date | None, hoje: date) -> StatusVacina:
    """H5.7. `hoje` e o dia em Brasilia (hoje_na_ong)."""
    if proxima_dose is None:
        return StatusVacina.SEM_REFORCO
    if proxima_dose < hoje:
        return StatusVacina.VENCIDA
    if proxima_dose <= hoje + timedelta(days=JANELA_VENCENDO_DIAS):
        return StatusVacina.VENCENDO
    return StatusVacina.EM_DIA


# ------------------------------------------------------------------ catalogo


async def listar_vacinas(sessao: AsyncSession, incluir_inativas: bool) -> list[Vacina]:
    return await repo_vacina.listar_vacinas(sessao, incluir_inativas)


async def criar_vacina(sessao: AsyncSession, dados: VacinaCriar) -> Vacina:
    if await repo_vacina.nome_em_uso(sessao, dados.nome):
        raise ConflitoError(_NOME_EM_USO)
    vacina = Vacina(
        nome=dados.nome,
        especie=dados.especie,
        intervalo_reforco_dias=dados.intervalo_reforco_dias,
    )
    sessao.add(vacina)
    # Dois cadastros iguais ao mesmo tempo passam juntos pela consulta: o indice barra o
    # segundo, que recebe o mesmo 409.
    await gravar_sem_duplicar(sessao, sessao.commit(), _NOME_EM_USO, erro=ConflitoError)
    await sessao.refresh(vacina)
    return vacina


async def atualizar_vacina(sessao: AsyncSession, vacina_id: int, dados: VacinaAtualizar) -> Vacina:
    vacina = await repo_vacina.obter_vacina_com_lock(sessao, vacina_id)
    if vacina is None:
        raise RecursoNaoEncontradoError(f"Vacina {vacina_id} nao encontrada.")

    campos = dados.model_dump(exclude_unset=True)
    nome = campos.get("nome")
    if nome is not None and await repo_vacina.nome_em_uso(sessao, nome, exceto_id=vacina.id):
        raise ConflitoError(_NOME_EM_USO)
    for campo, valor in campos.items():
        setattr(vacina, campo, valor)

    await gravar_sem_duplicar(sessao, sessao.commit(), _NOME_EM_USO, erro=ConflitoError)
    await sessao.refresh(vacina)
    return vacina


# ------------------------------------------------------------------- cartao


async def registrar_aplicacao(
    sessao: AsyncSession, pet_id: int, dados: AplicacaoCriar, veterinario: Usuario, hoje: date
) -> AplicacaoVacina:
    pet = await repo_pet.obter_por_id(sessao, pet_id)
    if pet is None:
        raise RecursoNaoEncontradoError(f"Pet {pet_id} nao encontrado.")
    if dados.data_aplicacao > hoje:
        raise RegraNegocioError("A data da aplicacao nao pode estar no futuro.")

    # FOR SHARE: uma desativacao simultanea espera esta aplicacao, ou esta ve a vacina ja
    # desativada -- nunca uma aplicacao nova numa vacina que acabou de sair do catalogo.
    vacina = await repo_vacina.obter_vacina_com_lock(sessao, dados.vacina_id, compartilhado=True)
    if vacina is None:
        raise RecursoNaoEncontradoError(f"Vacina {dados.vacina_id} nao encontrada.")
    if not vacina.ativa:
        raise RegraNegocioError(
            f"A vacina {vacina.nome} esta inativa no catalogo e nao recebe aplicacoes novas."
        )
    if vacina.especie is not None and vacina.especie != pet.especie:
        raise RegraNegocioError(
            f"A vacina {vacina.nome} e para {vacina.especie.value}, e este pet e "
            f"{pet.especie.value}."
        )
    if await repo_vacina.existe_aplicacao_valida(sessao, pet_id, vacina.id, dados.data_aplicacao):
        raise ConflitoError(_APLICACAO_REPETIDA)

    aplicacao = AplicacaoVacina(
        pet_id=pet_id,
        vacina_id=vacina.id,
        veterinario_id=veterinario.id,
        data_aplicacao=dados.data_aplicacao,
        proxima_dose=dados.proxima_dose,
        lote=dados.lote,
        observacao=dados.observacao,
    )
    sessao.add(aplicacao)
    await gravar_sem_duplicar(sessao, sessao.commit(), _APLICACAO_REPETIDA, erro=ConflitoError)
    return await _com_nomes(sessao, aplicacao.id)


async def anular_aplicacao(
    sessao: AsyncSession, aplicacao_id: int, dados: AplicacaoAnular, veterinario: Usuario
) -> AplicacaoVacina:
    aplicacao = await repo_vacina.obter_aplicacao_com_lock(sessao, aplicacao_id)
    if aplicacao is None:
        raise RecursoNaoEncontradoError(f"Aplicacao de vacina {aplicacao_id} nao encontrada.")
    if aplicacao.anulado_em is not None:
        raise RegraNegocioError("Esta aplicacao ja foi anulada.")

    # Relogio do banco, o mesmo do criado_em.
    aplicacao.anulado_em = func.now()
    aplicacao.anulado_por_id = veterinario.id
    aplicacao.motivo_anulacao = dados.motivo
    await sessao.commit()
    return await _com_nomes(sessao, aplicacao.id)


async def montar_cartao(sessao: AsyncSession, pet_id: int, hoje: date) -> CartaoVacinacao:
    if await repo_pet.obter_por_id(sessao, pet_id) is None:
        raise RecursoNaoEncontradoError(f"Pet {pet_id} nao encontrado.")

    ultimas = await repo_vacina.ultimas_validas_do_pet(sessao, pet_id)
    situacao = [
        SituacaoVacina(
            vacina_id=aplicacao.vacina_id,
            vacina_nome=aplicacao.vacina.nome,
            vacina_ativa=aplicacao.vacina.ativa,
            ultima_aplicacao=aplicacao.data_aplicacao,
            proxima_dose=aplicacao.proxima_dose,
            status=status_da_dose(aplicacao.proxima_dose, hoje),
            dias_para_vencer=(
                (aplicacao.proxima_dose - hoje).days if aplicacao.proxima_dose else None
            ),
        )
        for aplicacao in ultimas
    ]
    situacao.sort(
        key=lambda item: (
            _PRIORIDADE[item.status],
            item.proxima_dose or date.max,
            item.vacina_nome.lower(),
        )
    )

    historico = await repo_vacina.historico_do_pet(sessao, pet_id)
    return CartaoVacinacao(
        pet_id=pet_id,
        hoje=hoje,
        situacao=situacao,
        historico=[AplicacaoResposta.model_validate(item) for item in historico],
    )


async def _com_nomes(sessao: AsyncSession, aplicacao_id: int) -> AplicacaoVacina:
    aplicacao = await repo_vacina.obter_aplicacao(sessao, aplicacao_id)
    assert aplicacao is not None  # acabou de ser gravada nesta sessao
    return aplicacao


# ------------------------------------------------------------------ alertas


async def montar_alertas(sessao: AsyncSession, hoje: date, limite: int) -> AlertasVacina:
    """Vacinas vencidas e vencendo em ate 30 dias, das mais atrasadas primeiro (H6).

    O corte e o mesmo do cartao: o banco seleciona ate hoje + JANELA_VENCENDO_DIAS e o
    status de cada item vem de status_da_dose, a mesma funcao do cartao.
    """
    ate = hoje + timedelta(days=JANELA_VENCENDO_DIAS)
    linhas, vencidas, vencendo = await repo_vacina.alertas(sessao, hoje, ate, limite)
    itens = []
    for aplicacao, pet_nome, vacina_nome in linhas:
        assert aplicacao.proxima_dose is not None  # o filtro da consulta garante
        itens.append(
            AlertaVacina(
                pet_id=aplicacao.pet_id,
                pet_nome=pet_nome,
                vacina_id=aplicacao.vacina_id,
                vacina_nome=vacina_nome,
                proxima_dose=aplicacao.proxima_dose,
                status=status_da_dose(aplicacao.proxima_dose, hoje),
                dias_para_vencer=(aplicacao.proxima_dose - hoje).days,
            )
        )
    return AlertasVacina(hoje=hoje, total_vencidas=vencidas, total_vencendo=vencendo, itens=itens)
