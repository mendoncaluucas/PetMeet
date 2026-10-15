"""Acesso a dados do catalogo de vacinas e do cartao de vacinacao (fase 2, H4 e H5)."""

from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, joinedload

from app.modelos.enums import SituacaoAdocaoPet
from app.modelos.pet import Pet
from app.modelos.vacina import AplicacaoVacina, Vacina, chave_do_nome_vacina

# ------------------------------------------------------------------ catalogo


async def listar_vacinas(sessao: AsyncSession, incluir_inativas: bool) -> list[Vacina]:
    # Pela chave (casefold no Python): a ordem nao muda com a collation do banco.
    consulta = select(Vacina).order_by(Vacina.nome_chave)
    if not incluir_inativas:
        consulta = consulta.where(Vacina.ativa.is_(True))
    return list((await sessao.execute(consulta)).scalars().all())


async def obter_vacina_com_lock(
    sessao: AsyncSession, vacina_id: int, *, compartilhado: bool = False
) -> Vacina | None:
    """FOR UPDATE para editar; FOR SHARE ao registrar uma aplicacao.

    Assim, desativar a vacina espera a aplicacao em andamento terminar, e a aplicacao que
    chega depois ja ve a vacina inativa -- o mesmo par usado com o adotante na adocao.
    """
    consulta = (
        select(Vacina)
        .where(Vacina.id == vacina_id)
        .with_for_update(read=compartilhado)
        .execution_options(populate_existing=True)
    )
    return (await sessao.execute(consulta)).scalar_one_or_none()


async def nome_em_uso(sessao: AsyncSession, nome: str, *, exceto_id: int | None = None) -> bool:
    """Mesma chave da unicidade no banco (chave_do_nome_vacina)."""
    consulta = select(Vacina.id).where(Vacina.nome_chave == chave_do_nome_vacina(nome))
    if exceto_id is not None:
        consulta = consulta.where(Vacina.id != exceto_id)
    return (await sessao.execute(consulta.limit(1))).first() is not None


# ------------------------------------------------------------------- cartao

_COM_NOMES = (
    joinedload(AplicacaoVacina.vacina),
    joinedload(AplicacaoVacina.veterinario),
    joinedload(AplicacaoVacina.anulado_por),
)


async def obter_aplicacao(sessao: AsyncSession, aplicacao_id: int) -> AplicacaoVacina | None:
    consulta = (
        select(AplicacaoVacina)
        .where(AplicacaoVacina.id == aplicacao_id)
        .options(*_COM_NOMES)
        .execution_options(populate_existing=True)
    )
    return (await sessao.execute(consulta)).scalar_one_or_none()


async def obter_aplicacao_com_lock(
    sessao: AsyncSession, aplicacao_id: int
) -> AplicacaoVacina | None:
    """Sem os nomes: o Postgres nao trava o lado opcional de um LEFT JOIN."""
    consulta = (
        select(AplicacaoVacina)
        .where(AplicacaoVacina.id == aplicacao_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return (await sessao.execute(consulta)).scalar_one_or_none()


async def existe_aplicacao_valida(
    sessao: AsyncSession, pet_id: int, vacina_id: int, data_aplicacao: date
) -> bool:
    consulta = select(AplicacaoVacina.id).where(
        AplicacaoVacina.pet_id == pet_id,
        AplicacaoVacina.vacina_id == vacina_id,
        AplicacaoVacina.data_aplicacao == data_aplicacao,
        AplicacaoVacina.anulado_em.is_(None),
    )
    return (await sessao.execute(consulta.limit(1))).first() is not None


async def historico_do_pet(sessao: AsyncSession, pet_id: int) -> list[AplicacaoVacina]:
    """Todas as aplicacoes, anuladas inclusive: mais recente primeiro."""
    consulta = (
        select(AplicacaoVacina)
        .where(AplicacaoVacina.pet_id == pet_id)
        .options(*_COM_NOMES)
        .order_by(AplicacaoVacina.data_aplicacao.desc(), AplicacaoVacina.id.desc())
    )
    return list((await sessao.execute(consulta)).scalars().all())


def consulta_ultimas_validas() -> Select[AplicacaoVacina]:
    """A ultima aplicacao valida de cada vacina em cada pet (H5.7).

    E ela que decide o status: uma dose antiga com reforco vencido nao conta se ja houve
    dose mais nova (A-10), e a anulada nao conta nunca (H5.9). No empate de data, vale a
    registrada por ultimo. Os alertas da H6 partem desta mesma consulta.
    """
    return (
        select(AplicacaoVacina)
        .where(AplicacaoVacina.anulado_em.is_(None))
        .ext(distinct_on(AplicacaoVacina.pet_id, AplicacaoVacina.vacina_id))
        .order_by(
            AplicacaoVacina.pet_id,
            AplicacaoVacina.vacina_id,
            AplicacaoVacina.data_aplicacao.desc(),
            AplicacaoVacina.id.desc(),
        )
    )


async def ultimas_validas_do_pet(sessao: AsyncSession, pet_id: int) -> list[AplicacaoVacina]:
    consulta = (
        consulta_ultimas_validas()
        .where(AplicacaoVacina.pet_id == pet_id)
        .options(joinedload(AplicacaoVacina.vacina))
    )
    return list((await sessao.execute(consulta)).scalars().all())


# ------------------------------------------------------------------ alertas


async def alertas(
    sessao: AsyncSession, hoje: date, ate: date, limite: int
) -> tuple[list[tuple[AplicacaoVacina, str, str]], int, int]:
    """Alertas de vencimento (H6): a ultima dose valida de cada vacina, em pet nao adotado,
    com proxima dose ate `ate`. Das mais atrasadas para as mais distantes.

    Devolve (itens, total de vencidas, total vencendo). Vencida: proxima dose antes de
    `hoje`; vencendo: de `hoje` ate `ate`. Os totais sao contados no banco, sobre todos os
    alertas, e nao sobre a lista limitada.

    - D6: pet adotado fica de fora -- a responsabilidade passa ao adotante.
    - H4.4: vacina desativada continua -- a dose dela segue vencendo no pet.
    """
    ultima = aliased(AplicacaoVacina, consulta_ultimas_validas().subquery())
    filtro = (
        Pet.situacao_adocao != SituacaoAdocaoPet.ADOTADO,
        ultima.proxima_dose.is_not(None),
        ultima.proxima_dose <= ate,
    )

    totais = (
        select(
            func.count().filter(ultima.proxima_dose < hoje),
            func.count().filter(ultima.proxima_dose >= hoje),
        )
        .select_from(ultima)
        .join(Pet, Pet.id == ultima.pet_id)
        .where(*filtro)
    )
    vencidas, vencendo = (await sessao.execute(totais)).one()

    consulta = (
        select(ultima, Pet.nome, Vacina.nome)
        .join(Pet, Pet.id == ultima.pet_id)
        .join(Vacina, Vacina.id == ultima.vacina_id)
        .where(*filtro)
        .order_by(ultima.proxima_dose, Pet.nome, Vacina.nome_chave)
        .limit(limite)
    )
    linhas = (await sessao.execute(consulta)).all()
    return [(aplicacao, pet, vacina) for aplicacao, pet, vacina in linhas], vencidas, vencendo
