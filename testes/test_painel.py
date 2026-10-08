"""Resumo do Painel calculado no banco (DEF-09, DEF-10)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tempo import hoje_na_ong, intervalo_do_mes
from app.modelos.doacao import Doacao
from app.modelos.enums import FrequenciaContribuicao, StatusSaudePet
from app.modelos.pet import Pet
from app.servicos import painel as servico_painel


def _doacao(valor: str, dia: date) -> Doacao:
    return Doacao(
        doador_nome="Doador", valor=Decimal(valor), data=dia, tipo=FrequenciaContribuicao.PONTUAL
    )


def test_as_21h30_do_ultimo_dia_do_mes_ainda_e_o_mesmo_mes() -> None:
    """DEF-09: o Painel usava o mes em UTC; as 21h30 de 31/10 em Brasilia ja e 01/11 em UTC."""
    agora = datetime(2026, 11, 1, 0, 30, tzinfo=UTC)  # 31/10 21:30 em Brasilia

    assert hoje_na_ong(agora) == date(2026, 10, 31)


def test_intervalo_do_mes_vira_o_ano_em_dezembro() -> None:
    assert intervalo_do_mes(date(2026, 12, 15)) == (date(2026, 12, 1), date(2027, 1, 1))


async def test_doacoes_do_mes_contam_o_mes_da_ong(sessao: AsyncSession) -> None:
    sessao.add_all(
        [
            _doacao("50.00", date(2026, 10, 31)),
            _doacao("20.00", date(2026, 10, 1)),
            _doacao("30.00", date(2026, 11, 1)),
        ]
    )
    await sessao.commit()

    resumo = await servico_painel.montar_resumo(sessao, hoje=date(2026, 10, 31))

    assert resumo.mes_de_referencia == "2026-10"
    assert resumo.doacoes_do_mes_total == Decimal("70.00")
    assert resumo.doacoes_do_mes_quantidade == 2


async def test_contagens_e_total_passam_de_100_registros(
    client: AsyncClient, cabecalho_admin: dict, sessao: AsyncSession
) -> None:
    """DEF-10: o Painel somava so as primeiras 100 linhas de cada listagem."""
    sessao.add_all(
        Pet(nome=f"Pet {i}", especie="gato", idade=1, data_resgate=date(2026, 1, 1))
        for i in range(120)
    )
    sessao.add_all(
        Pet(
            nome=f"Tratamento {i}",
            especie="gato",
            idade=1,
            data_resgate=date(2026, 1, 1),
            status_saude=StatusSaudePet.EM_TRATAMENTO_MEDICO,
            doenca_atual="Cinomose",
        )
        for i in range(3)
    )
    sessao.add_all(_doacao("10.00", hoje_na_ong()) for _ in range(105))
    await sessao.commit()

    resposta = await client.get("/painel/resumo", headers=cabecalho_admin)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["pets_total"] == 123
    assert corpo["pets_disponiveis"] == 123
    assert corpo["pets_em_tratamento"] == 3
    assert Decimal(corpo["doacoes_do_mes_total"]) == Decimal("1050.00")
    assert corpo["doacoes_do_mes_quantidade"] == 105


async def test_esperando_ha_mais_tempo_acha_o_pet_mais_antigo(sessao: AsyncSession) -> None:
    """O Painel ordenava so os 100 cadastrados mais recentemente; o mais antigo ficava de fora."""
    sessao.add(Pet(nome="Veterano", especie="cachorro", idade=9, data_resgate=date(2019, 5, 1)))
    await sessao.commit()
    inicio = date(2026, 1, 1)
    sessao.add_all(
        Pet(nome=f"Novo {i}", especie="gato", idade=1, data_resgate=inicio + timedelta(days=i))
        for i in range(120)
    )
    await sessao.commit()

    resumo = await servico_painel.montar_resumo(sessao, hoje=date(2026, 10, 8))

    assert resumo.esperando_ha_mais_tempo[0].nome == "Veterano"


async def test_resumo_exige_login(client: AsyncClient) -> None:
    resposta = await client.get("/painel/resumo")
    assert resposta.status_code == 401
