"""Fase 2, H6: alertas de vencimento de vacina (criterios em docs/HISTORIAS-FASE-2.md)."""

from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import hoje_na_ong
from app.esquemas.vacina import StatusVacina
from app.modelos.enums import EspeciePet, PerfilUsuario, SituacaoAdocaoPet
from app.modelos.pet import Pet
from app.modelos.usuario import Usuario
from app.modelos.vacina import AplicacaoVacina, Vacina
from app.servicos import vacinacao as servico_vacinacao
from testes.conftest import cabecalho_do_perfil

HOJE = date(2026, 10, 15)


def _dia(deslocamento: int) -> date:
    return HOJE + timedelta(days=deslocamento)


class _Cenario:
    """Monta pets, vacinas e aplicacoes direto no banco, com um veterinario so."""

    def __init__(self, sessao: AsyncSession, hoje: date = HOJE) -> None:
        self.sessao = sessao
        self.hoje = hoje  # as datas das aplicacoes sao relativas a este dia
        self.veterinario: Usuario | None = None

    async def pet(
        self, nome: str, situacao: SituacaoAdocaoPet = SituacaoAdocaoPet.DISPONIVEL
    ) -> Pet:
        pet = Pet(
            nome=nome,
            especie=EspeciePet.CACHORRO,
            idade=2,
            data_resgate=date(2025, 1, 1),
            situacao_adocao=situacao,
        )
        self.sessao.add(pet)
        await self.sessao.commit()
        return pet

    async def vacina(self, nome: str, ativa: bool = True) -> Vacina:
        vacina = Vacina(nome=nome, especie=None, ativa=ativa)
        self.sessao.add(vacina)
        await self.sessao.commit()
        return vacina

    async def aplicar(
        self,
        pet: Pet,
        vacina: Vacina,
        proxima: int | None,
        aplicada: int = -300,
        anulada: bool = False,
    ) -> AplicacaoVacina:
        if self.veterinario is None:
            self.veterinario = Usuario(
                nome="Dra. Paula",
                email="paula@x.org",
                senha_hash="x",
                perfil=PerfilUsuario.VETERINARIO,
            )
            self.sessao.add(self.veterinario)
            await self.sessao.commit()
        aplicacao = AplicacaoVacina(
            pet_id=pet.id,
            vacina_id=vacina.id,
            veterinario_id=self.veterinario.id,
            data_aplicacao=self.hoje + timedelta(days=aplicada),
            proxima_dose=None if proxima is None else self.hoje + timedelta(days=proxima),
        )
        if anulada:
            aplicacao.anulado_em = datetime.now(UTC)
            aplicacao.anulado_por_id = self.veterinario.id
            aplicacao.motivo_anulacao = "teste"
        self.sessao.add(aplicacao)
        await self.sessao.commit()
        return aplicacao


async def _alertas(sessao: AsyncSession, hoje: date = HOJE, limite: int = 50):
    return await servico_vacinacao.montar_alertas(sessao, hoje=hoje, limite=limite)


# ------------------------------------------------------------------- H6.1-2


async def test_so_vencidas_e_vencendo_das_mais_atrasadas_primeiro(sessao: AsyncSession) -> None:
    c = _Cenario(sessao)
    rex = await c.pet("Rex")
    v10, raiva, giardia, gripe = (
        await c.vacina("V10"),
        await c.vacina("Antirrabica"),
        await c.vacina("Giardia"),
        await c.vacina("Gripe"),
    )
    await c.aplicar(rex, v10, proxima=-20)  # vencida ha 20 dias
    await c.aplicar(rex, raiva, proxima=10)  # vencendo
    await c.aplicar(rex, giardia, proxima=200)  # em dia: nao e alerta
    await c.aplicar(rex, gripe, proxima=None)  # sem reforco: nao e alerta

    alertas = await _alertas(sessao)

    assert alertas.hoje == HOJE
    assert (alertas.total_vencidas, alertas.total_vencendo) == (1, 1)
    assert [(item.vacina_nome, item.status, item.dias_para_vencer) for item in alertas.itens] == [
        ("V10", StatusVacina.VENCIDA, -20),
        ("Antirrabica", StatusVacina.VENCENDO, 10),
    ]
    assert alertas.itens[0].pet_nome == "Rex"


async def test_janela_de_30_dias_inclui_hoje_e_o_trigesimo_dia(sessao: AsyncSession) -> None:
    c = _Cenario(sessao)
    rex = await c.pet("Rex")
    for nome, proxima in (("Hoje", 0), ("Dia30", 30), ("Dia31", 31), ("Ontem", -1)):
        await c.aplicar(rex, await c.vacina(nome), proxima=proxima)

    alertas = await _alertas(sessao)

    assert [(item.vacina_nome, item.status) for item in alertas.itens] == [
        ("Ontem", StatusVacina.VENCIDA),
        ("Hoje", StatusVacina.VENCENDO),
        ("Dia30", StatusVacina.VENCENDO),
    ]


async def test_totais_do_banco_batem_com_o_status_do_cartao(sessao: AsyncSession) -> None:
    """A regra existe em SQL (totais) e em Python (status). Nas datas de fronteira, as duas
    tem de concordar -- se uma mudar sem a outra, este teste falha."""
    c = _Cenario(sessao)
    rex = await c.pet("Rex")
    for deslocamento in (-31, -1, 0, 1, 29, 30, 31):
        await c.aplicar(rex, await c.vacina(f"V{deslocamento}"), proxima=deslocamento)

    alertas = await _alertas(sessao)
    pelo_status = [
        servico_vacinacao.status_da_dose(_dia(d), HOJE) for d in (-31, -1, 0, 1, 29, 30, 31)
    ]

    assert alertas.total_vencidas == pelo_status.count(StatusVacina.VENCIDA)
    assert alertas.total_vencendo == pelo_status.count(StatusVacina.VENCENDO)
    assert len(alertas.itens) == alertas.total_vencidas + alertas.total_vencendo


async def test_totais_contam_todos_os_alertas_e_nao_so_a_lista(sessao: AsyncSession) -> None:
    c = _Cenario(sessao)
    for indice in range(3):
        pet = await c.pet(f"Pet {indice}")
        await c.aplicar(pet, await c.vacina(f"Vacina {indice}"), proxima=-indice - 1)

    alertas = await _alertas(sessao, limite=1)

    assert alertas.total_vencidas == 3
    assert len(alertas.itens) == 1
    assert alertas.itens[0].dias_para_vencer == -3  # a mais atrasada


# --------------------------------------------------------------- H6.2 e A-10


async def test_vale_a_ultima_dose_valida(sessao: AsyncSession) -> None:
    """A dose antiga vencida nao gera alerta se ja houve dose nova; anulada a nova, volta."""
    c = _Cenario(sessao)
    rex = await c.pet("Rex")
    v10 = await c.vacina("V10")
    await c.aplicar(rex, v10, aplicada=-400, proxima=-35)
    nova = await c.aplicar(rex, v10, aplicada=-35, proxima=330)

    sem_alerta = await _alertas(sessao)
    nova.anulado_em = datetime.now(UTC)
    nova.anulado_por_id = c.veterinario.id
    nova.motivo_anulacao = "Pet errado"
    await sessao.commit()
    com_alerta = await _alertas(sessao)

    assert sem_alerta.itens == []
    assert [(item.status, item.dias_para_vencer) for item in com_alerta.itens] == [
        (StatusVacina.VENCIDA, -35)
    ]


# --------------------------------------------------------------------- H6.3


async def test_pet_adotado_nao_entra_e_em_processo_entra(sessao: AsyncSession) -> None:
    c = _Cenario(sessao)
    v10 = await c.vacina("V10")
    for nome, situacao in (
        ("Disponivel", SituacaoAdocaoPet.DISPONIVEL),
        ("Em processo", SituacaoAdocaoPet.EM_PROCESSO_ADOCAO),
        ("Adotado", SituacaoAdocaoPet.ADOTADO),
    ):
        await c.aplicar(await c.pet(nome, situacao), v10, proxima=-5)

    alertas = await _alertas(sessao)

    assert sorted(item.pet_nome for item in alertas.itens) == ["Disponivel", "Em processo"]
    assert alertas.total_vencidas == 2


async def test_vacina_desativada_continua_alertando(sessao: AsyncSession) -> None:
    """H4.4: a dose de uma vacina que saiu do catalogo continua vencendo no pet."""
    c = _Cenario(sessao)
    await c.aplicar(await c.pet("Rex"), await c.vacina("FeLV", ativa=False), proxima=-3)

    alertas = await _alertas(sessao)

    assert [item.vacina_nome for item in alertas.itens] == ["FeLV"]


# --------------------------------------------------------------------- H6.4


async def test_hoje_e_o_dia_de_brasilia(sessao: AsyncSession) -> None:
    """23h de 15/10 em Brasilia ja e 16/10 em UTC. Dose para 16/10: ainda vence amanha,
    nao "vence hoje"; e so fica vencida em 17/10."""
    c = _Cenario(sessao)
    await c.aplicar(await c.pet("Rex"), await c.vacina("V10"), proxima=1)  # 16/10

    as_23h = hoje_na_ong(datetime(2026, 10, 16, 2, 0, tzinfo=UTC))
    na_vespera = await _alertas(sessao, hoje=as_23h)
    no_dia = await _alertas(sessao, hoje=date(2026, 10, 16))
    depois = await _alertas(sessao, hoje=date(2026, 10, 17))

    assert as_23h == date(2026, 10, 15)
    assert [(i.status, i.dias_para_vencer) for i in na_vespera.itens] == [
        (StatusVacina.VENCENDO, 1)
    ]
    assert [(i.status, i.dias_para_vencer) for i in no_dia.itens] == [(StatusVacina.VENCENDO, 0)]
    assert [(i.status, i.dias_para_vencer) for i in depois.itens] == [(StatusVacina.VENCIDA, -1)]


# ----------------------------------------------------------------- acesso


@pytest.mark.parametrize(
    "perfil", [PerfilUsuario.ADMIN, PerfilUsuario.VOLUNTARIO, PerfilUsuario.VETERINARIO]
)
async def test_equipe_e_veterinario_veem_os_alertas(
    client: AsyncClient, sessao: AsyncSession, perfil: PerfilUsuario
) -> None:
    hoje = hoje_na_ong()
    c = _Cenario(sessao, hoje=hoje)
    rex = await c.pet("Rex")
    v10 = await c.vacina("V10")
    await c.aplicar(rex, v10, proxima=-2)

    resposta = await client.get(
        "/vacinacao/alertas", headers=await cabecalho_do_perfil(sessao, perfil)
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["hoje"] == hoje.isoformat()
    assert corpo["total_vencidas"] == 1
    assert corpo["itens"][0] == {
        "pet_id": rex.id,
        "pet_nome": "Rex",
        "vacina_id": v10.id,
        "vacina_nome": "V10",
        "proxima_dose": (hoje - timedelta(days=2)).isoformat(),
        "status": "vencida",
        "dias_para_vencer": -2,
    }


async def test_limite_da_lista(client: AsyncClient, cabecalho_veterinario: dict) -> None:
    acima = await client.get("/vacinacao/alertas?limite=201", headers=cabecalho_veterinario)
    zero = await client.get("/vacinacao/alertas?limite=0", headers=cabecalho_veterinario)

    assert acima.status_code == 422
    assert zero.status_code == 422
